import asyncio
import logging
import sys
import time
from typing import NoReturn, Callable, Any, Coroutine

from analyze_mft.parsers.mft_parser import MFTParser, parse_mft
from analyze_mft.utilities.file_handler import FileHandler
from analyze_mft.outputs.csv_writer import CSVWriter
from analyze_mft.parsers.options_parser import OptionsParser
from analyze_mft.utilities.logger import Logger
from analyze_mft.utilities.thread_manager import ThreadManager
from analyze_mft.outputs.json_writer import JSONWriter
from analyze_mft.utilities.error_handler import error_handler

class TimeoutError(Exception):
    pass

async def run_with_timeout(coro: Coroutine, timeout_duration: int = 300) -> Any:
    try:
        return await asyncio.wait_for(coro, timeout=timeout_duration)
    except asyncio.TimeoutError:
        raise TimeoutError(f"Function call timed out after {timeout_duration} seconds")

@error_handler
async def initialize_components(options):
    logger = Logger(options)
    file_handler = FileHandler(options)
    async with file_handler as fh:
        csv_writer = CSVWriter(options, fh)
        json_writer = JSONWriter(options, fh)
        thread_manager = ThreadManager(options.thread_count)
   
        return logger, fh, csv_writer, json_writer, thread_manager

@error_handler
async def parse_mft(mft_parser: MFTParser) -> None:
    await mft_parser.generate_filepaths()
    await mft_parser.print_records()

async def main() -> NoReturn:
    options_parser = OptionsParser()
    options = options_parser.parse_options()

    logger, file_handler, csv_writer, json_writer, thread_manager = await initialize_components(options)
    logger.info("Starting analyzeMFT")

    async with FileHandler(options) as file_handler:
        csv_writer = CSVWriter(options, file_handler)
   
        mft_parser = MFTParser(options, file_handler, csv_writer, json_writer, thread_manager)
       
        logger.info("Initializing the MFT parsing object...")
       

        start_time = time.time()
        total_records = await mft_parser.get_total_records()  
        
        logger.info(f"Starting to parse {total_records} records...")
        
        try:
            await run_with_timeout(parse_mft(mft_parser), timeout_duration=600)  
        except TimeoutError:
            logger.error("MFT parsing timed out after 1 hour")
            sys.exit(1)
        except Exception as e:
            logger.error(f"An error occurred during MFT parsing: {str(e)}")
            sys.exit(1)
        
        end_time = time.time()
        logger.info(f"MFT parsing completed in {end_time - start_time:.2f} seconds")

    logger.info("analyzeMFT completed successfully.")
    sys.exit(0)

if __name__ == "__main__":
    asyncio.run(main())