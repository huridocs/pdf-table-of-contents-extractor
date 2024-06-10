import logging
from pathlib import Path
from pdf_token_type_labels.TokenType import TokenType

SRC_PATH = Path(__file__).parent.absolute()
ROOT_PATH = Path(__file__).parent.parent.absolute()

title_types = {TokenType.TITLE, TokenType.SECTION_HEADER}
skip_types = {TokenType.TITLE, TokenType.SECTION_HEADER, TokenType.PAGE_HEADER, TokenType.PICTURE}

handlers = [logging.StreamHandler()]
logging.root.handlers = []
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", handlers=handlers)
service_logger = logging.getLogger(__name__)
