import string
import roman
import numpy as np
from pdf_features.PdfFeatures import PdfFeatures
from pdf_features.PdfFont import PdfFont
from paragraph_extraction_trainer.PdfSegment import PdfSegment
from pdf_features.PdfToken import PdfToken
from pdf_features.Rectangle import Rectangle
from pdf_token_type_labels.TokenType import TokenType
from src.data.SegmentBox import SegmentBox
from src.toc.data.TOCItem import TOCItem
from src.toc.methods.two_models_v3_segments_context_2.Modes import Modes
from src.toc.PdfSegmentation import PdfSegmentation


class TitleFeatures:
    SPECIAL_MARKERS = [".", "(", ")", "\\", "/", ":", ";", "-", "_", "[", "]", "•", "◦", "*", ","]
    ALPHABET = list(string.ascii_lowercase)
    ALPHABET_UPPERCASE = list(string.ascii_uppercase)
    ROMAN_NUMBERS = [roman.toRoman(i) for i in range(1, 151)]
    ROMAN_NUMBERS_LOWERCASE = [x.lower() for x in ROMAN_NUMBERS]
    BULLET_POINTS = [ALPHABET, ALPHABET_UPPERCASE, ROMAN_NUMBERS, ROMAN_NUMBERS_LOWERCASE]

    def __init__(self, pdf_segment: PdfSegment, pdf_features: PdfFeatures, modes: Modes):
        self.modes = modes
        self.pdf_segment = pdf_segment
        self.pdf_features = pdf_features

        self.segment_tokens: list[PdfToken] = []
        self.first_characters: str = ""
        self.first_characters_special_markers_count: int = 0
        self.font_size: float = 0.0
        self.text_content: str = ""
        self.width: float = 0
        self.font_family: str = ""
        self.font_color: str = ""
        self.line_height: float = 0.0
        self.uppercase: bool = False
        self.bold: float = False
        self.italics: float = False
        self.first_characters_type = 0
        self.bullet_points_type = 0
        self.text_centered: int = 0
        self.is_left: bool = False
        self.indentation: int = -1
        self.left: int = 0
        self.right: int = 0
        self.top: int = 0
        self.bottom: int = 0

        self.initialize_segment_tokens()
        self.initialize_text_properties()
        self.process_first_characters()
        self.process_font_properties()
        self.process_positional_properties()

    def initialize_segment_tokens(self):
        self.segment_tokens: list[PdfToken] = [
            pdf_token
            for page, pdf_token in self.pdf_features.loop_tokens()
            if self.pdf_segment.page_number == pdf_token.page_number
            and pdf_token.bounding_box.get_intersection_percentage(self.pdf_segment.bounding_box) > 50
        ]
        self.segment_tokens = self.segment_tokens if self.segment_tokens else [self.get_one_token()]

    def initialize_text_properties(self):
        words = [token.content for token in self.segment_tokens]
        self.text_content = " ".join(words)

    def process_first_characters(self):
        self.first_characters = self.text_content.split(" ")[0].split("\n")[0].split("\t")[0]
        clean_first_characters = [x for x in self.first_characters if x not in self.SPECIAL_MARKERS]
        characters_checker = {
            1: lambda x_list: len(x_list) == len([letter for letter in x_list if letter in "IVXL"]),
            2: lambda x_list: len(x_list) == len([letter for letter in x_list if letter in "IVXL".lower()]),
            3: lambda x_list: len(x_list) == len([letter for letter in x_list if letter in "1234567890"]),
            4: lambda x_list: len(x_list) == len([letter for letter in x_list if letter == letter.upper()]),
        }

        self.first_characters_type = next((index for index, type_checker in characters_checker.items()
                                           if type_checker(clean_first_characters)), 0)

        self.bullet_points_type = (
            self.SPECIAL_MARKERS.index(self.first_characters[-1]) + 1
            if self.first_characters[-1] in self.SPECIAL_MARKERS
            else 0
        )
        self.first_characters_special_markers_count = len([x for x in self.first_characters[:-1] if x in self.SPECIAL_MARKERS])

    def process_font_properties(self):
        self.font_family = self.segment_tokens[0].font.font_id
        self.font_color = self.segment_tokens[0].font.color
        self.bold = sum(token.font.bold for token in self.segment_tokens) / len(self.segment_tokens)
        self.italics = sum(token.font.italics for token in self.segment_tokens) / len(self.segment_tokens)
        self.uppercase = self.text_content.upper() == self.text_content
        font_sizes = [token.font.font_size for token in self.segment_tokens]
        self.font_size = np.mean(font_sizes)

    def process_positional_properties(self):
        self.left = min(token.bounding_box.left for token in self.segment_tokens)
        self.top = min(token.bounding_box.top for token in self.segment_tokens)
        self.right = max(token.bounding_box.left + token.bounding_box.width for token in self.segment_tokens)
        self.bottom = max(token.bounding_box.left + token.bounding_box.width for token in self.segment_tokens)
        self.line_height = self.segment_tokens[0].font.font_size

        page_width = self.pdf_features.pages[self.pdf_segment.page_number-1].page_width
        self.text_centered = 1 if abs(self.left - (page_width - self.right)) < 10 else 0
        self.is_left = self.left < page_width - self.right if not self.text_centered else False
        self.indentation = int((self.left - self.modes.left_space_mode) / 15) if self.is_left else -1

    def get_features_to_merge(self) -> np.array:
        return (
            1 if self.bold else 0,
            1 if self.italics else 0,
        )

    def get_features_toc(self) -> np.array:
        return (
            1 if self.bold else 0,
            1 if self.italics else 0,
            self.first_characters_type,
            self.first_characters_special_markers_count,
            self.bullet_points_type
            # self.text_centered,
            # self.is_left,
            # self.indentation
        )

    def get_possible_previous_point(self) -> list[str]:
        previous_characters = self.first_characters
        final_special_markers = ""
        last_part = ""
        for letter in list(reversed(previous_characters)):
            if not last_part and letter in self.SPECIAL_MARKERS:
                final_special_markers = previous_characters[-1] + final_special_markers
                previous_characters = previous_characters[:-1]
                continue

            if last_part and letter in self.SPECIAL_MARKERS:
                break

            last_part = letter + last_part
            previous_characters = previous_characters[:-1]

        previous_items = self.get_previous_items(last_part)

        if not previous_items and len(self.first_characters) >= 4:
            return [self.first_characters]

        return [previous_characters + x + final_special_markers for x in previous_items]

    def get_previous_items(self, item: str):
        previous_items = []

        for bullet_points in self.BULLET_POINTS:
            if item in bullet_points and bullet_points.index(item):
                previous_items.append(bullet_points[bullet_points.index(item) - 1])

        if item.isnumeric():
            previous_items.append(str(int(item) - 1))

        return previous_items

    @staticmethod
    def from_pdf_segmentation(pdf_segmentation: PdfSegmentation) -> list["TitleFeatures"]:
        titles_features = list()
        modes = Modes(pdf_features=pdf_segmentation.pdf_features)
        for pdf_segment, title_prediction in pdf_segmentation.loop_predictions():
            # if title_prediction < 0.5:
            #     continue

            titles_features.append(TitleFeatures(pdf_segment, pdf_segmentation.pdf_features, modes))

        return titles_features

    def to_toc_item(self, indentation):
        segment_boxes = [SegmentBox.from_pdf_token(x) for x in self.segment_tokens]
        return TOCItem(
            indentation=indentation,
            label=self.text_content,
            selectionRectangles=segment_boxes,
        )

    def append(self, other_title_features: "TitleFeatures"):
        other_segment = other_title_features.pdf_segment
        merged_bounding_box = Rectangle.merge_rectangles([self.pdf_segment.bounding_box, other_segment.bounding_box])
        merged_content = self.pdf_segment.text_content + other_segment.text_content
        merged_segment = PdfSegment(self.pdf_segment.page_number, merged_bounding_box, merged_content, self.pdf_segment.segment_type)
        return TitleFeatures(pdf_segment=merged_segment, pdf_features=self.pdf_features, modes=self.modes)

    def get_one_token(self):
        for page, token in self.pdf_features.loop_tokens():
            return token

        font = PdfFont("font_id", False, False, 0, "#000000")
        bounding_box = Rectangle(0, 0, 0, 0)
        return PdfToken(0, "0", "", font, 0, bounding_box, TokenType.TEXT)
