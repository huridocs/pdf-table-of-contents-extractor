import tempfile
import uuid
from os.path import join
from pathlib import Path
from typing import AnyStr
from paragraph_extraction_trainer.PdfSegment import PdfSegment
from pdf_features.PdfFeatures import PdfFeatures
from pdf_features.Rectangle import Rectangle
from pdf_token_type_labels.TokenType import TokenType
from TOCExtractor import TOCExtractor
from configuration import service_logger, title_types
from toc.PdfSegmentation import PdfSegmentation


def get_file_path(file_name, extension):
    return join(tempfile.gettempdir(), file_name + "." + extension)


def pdf_content_to_pdf_path(file_content):
    file_id = str(uuid.uuid1())

    pdf_path = Path(get_file_path(file_id, "pdf"))
    pdf_path.write_bytes(file_content)

    return pdf_path


def get_pdf_segments_from_segment_boxes(pdf_features: PdfFeatures, segment_boxes: list[dict]) -> list[PdfSegment]:
    pdf_segments: list[PdfSegment] = []
    for segment_box in segment_boxes:
        left, top, width, height = segment_box["left"], segment_box["top"], segment_box["width"], segment_box["height"]
        bounding_box = Rectangle.from_width_height(left, top, width, height)
        segment_type = TokenType.from_text(segment_box["type"])
        pdf_name = pdf_features.file_name
        segment = PdfSegment(segment_box["page_number"], bounding_box, segment_box["text"], segment_type, pdf_name)
        pdf_segments.append(segment)
    return pdf_segments


def extract_table_of_contents(file: AnyStr, segment_boxes: list[dict]):
    service_logger.info("Getting TOC")
    pdf_path = pdf_content_to_pdf_path(file)
    pdf_features: PdfFeatures = PdfFeatures.from_pdf_path(pdf_path)
    pdf_segments: list[PdfSegment] = get_pdf_segments_from_segment_boxes(pdf_features, segment_boxes)
    title_segments = [segment for segment in pdf_segments if segment.segment_type in title_types]
    pdf_segmentation: PdfSegmentation = PdfSegmentation(pdf_features, title_segments)
    toc_instance: TOCExtractor = TOCExtractor(pdf_segmentation)
    return toc_instance.to_dict()
