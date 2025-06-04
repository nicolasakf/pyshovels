from pyshovels import ShovelsAPI, load_env
import logging
from pathlib import Path

def setup_logger(log_dir: Path, log_file: str):
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    # log to console
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.DEBUG)
    logger.addHandler(stream_handler)
    # log to file
    file_handler = logging.FileHandler(log_dir / log_file)
    file_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger

if __name__ == "__main__":
    load_env(env_path="./path/to/.env")
    log_dir = Path(__file__).parent
    logger = setup_logger(log_dir, 'paginated_request_with_logging.log')
    shovels = ShovelsAPI(logger=logger)
    response = shovels.search_contractors(
        params={
            "permit_from": "2025-04-01",
            "tag": "hvac",
        },
        geo_ids=["CA"],
        page=1,
        size=100,
        max_iterations=100,
    )
    print(response)
