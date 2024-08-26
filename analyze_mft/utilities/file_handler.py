import sys
from pathlib import Path
from typing import Optional, BinaryIO, TextIO
from dataclasses import dataclass

@dataclass
class FileHandlerOptions:
    filename: Path
    output: Optional[Path] = None
    bodyfile: Optional[Path] = None
    csvtimefile: Optional[Path] = None

class FileOpenError(Exception):
    pass

class FileHandler:
    def __init__(self, options: FileHandlerOptions):
        self.options = options
        self.file_mft: Optional[BinaryIO] = None
        self.file_csv: Optional[TextIO] = None
        self.file_body: Optional[TextIO] = None
        self.file_csv_time: Optional[TextIO] = None

    async def __aenter__(self):
        await self.open_files()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close_files()

    async def open_files(self):
        try:
            self.file_mft = await self._open_file(self.options.filename, 'rb')
            
            if self.options.output:
                self.file_csv = await self._open_file(self.options.output, 'w', newline='', encoding='utf-8')
            
            if self.options.bodyfile:
                self.file_body = await self._open_file(self.options.bodyfile, 'w', encoding='utf-8')
            
            if self.options.csvtimefile:
                self.file_csv_time = await self._open_file(self.options.csvtimefile, 'w', encoding='utf-8')
            
            if not self.file_mft:
                raise FileOpenError("MFT file not opened successfully.")
        
        except FileOpenError as e:
            print(f"Error: {str(e)}")
            sys.exit(1)

    async def _open_file(self, filename: Path, mode: str, **kwargs) -> BinaryIO | TextIO:
        try:
            return open(filename, mode, **kwargs)
        except IOError as e:
            raise FileOpenError(f"Unable to open file: {filename}. {e}")

    async def close_files(self):
        for file in [self.file_mft, self.file_csv, self.file_body, self.file_csv_time]:
            if file:
                file.close()

    async def read_mft_record(self) -> Optional[bytes]:
        if not self.file_mft:
            raise FileOpenError("MFT file is not open.")
        raw_record = self.file_mft.read(1024)
        return raw_record if raw_record else None

    async def estimate_total_records(self) -> int:
        if not self.file_mft:
            raise FileOpenError("MFT file is not open.")
        current_position = self.file_mft.tell()
        self.file_mft.seek(0, 2) 
        file_size = self.file_mft.tell()
        self.file_mft.seek(current_position) 
        return file_size // 1024  