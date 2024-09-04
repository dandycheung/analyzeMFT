import struct
import uuid
import hashlib
import zlib
from .constants import *
from .windows_time import WindowsTime


class MftRecord:
    def __init__(self, raw_record, compute_hashes=False):
        self.raw_record = raw_record
        self.magic = 0
        self.upd_off = 0
        self.upd_cnt = 0
        self.lsn = 0
        self.seq = 0
        self.link = 0
        self.attr_off = 0
        self.flags = 0
        self.size = 0
        self.alloc_sizef = 0
        self.base_ref = 0
        self.next_attrid = 0
        self.recordnum = 0
        self.filename = ''
        self.si_times = {
            'crtime': WindowsTime(0, 0),
            'mtime': WindowsTime(0, 0),
            'atime': WindowsTime(0, 0),
            'ctime': WindowsTime(0, 0)
        }
        self.fn_times = {
            'crtime': WindowsTime(0, 0),
            'mtime': WindowsTime(0, 0),
            'atime': WindowsTime(0, 0),
            'ctime': WindowsTime(0, 0)
        }
        self.filesize = 0
        self.attribute_types = set()
        self.object_id = ''
        self.birth_volume_id = ''
        self.birth_object_id = ''
        self.birth_domain_id = ''
        self.parent_ref = 0
        self.md5 = None
        self.sha256 = None
        self.sha512 = None
        self.crc32 = None
        if compute_hashes:
            self.compute_hashes()
        self.parse_record()


    def parse_record(self):
        try:
            self.magic = struct.unpack("<I", self.raw_record[MFT_RECORD_MAGIC_NUMBER_OFFSET:MFT_RECORD_MAGIC_NUMBER_OFFSET+MFT_RECORD_MAGIC_NUMBER_SIZE])[0]
            self.upd_off = struct.unpack("<H", self.raw_record[MFT_RECORD_UPDATE_SEQUENCE_OFFSET:MFT_RECORD_UPDATE_SEQUENCE_OFFSET+MFT_RECORD_UPDATE_SEQUENCE_SIZE])[0]
            self.upd_cnt = struct.unpack("<H", self.raw_record[MFT_RECORD_UPDATE_SEQUENCE_SIZE_OFFSET:MFT_RECORD_UPDATE_SEQUENCE_SIZE_OFFSET+MFT_RECORD_UPDATE_SEQUENCE_SIZE_SIZE])[0]
            self.lsn = struct.unpack("<Q", self.raw_record[MFT_RECORD_LOGFILE_SEQUENCE_NUMBER_OFFSET:MFT_RECORD_LOGFILE_SEQUENCE_NUMBER_OFFSET+MFT_RECORD_LOGFILE_SEQUENCE_NUMBER_SIZE])[0]
            self.seq = struct.unpack("<H", self.raw_record[MFT_RECORD_SEQUENCE_NUMBER_OFFSET:MFT_RECORD_SEQUENCE_NUMBER_OFFSET+MFT_RECORD_SEQUENCE_NUMBER_SIZE])[0]
            self.link = struct.unpack("<H", self.raw_record[MFT_RECORD_HARD_LINK_COUNT_OFFSET:MFT_RECORD_HARD_LINK_COUNT_OFFSET+MFT_RECORD_HARD_LINK_COUNT_SIZE])[0]
            self.attr_off = struct.unpack("<H", self.raw_record[MFT_RECORD_FIRST_ATTRIBUTE_OFFSET:MFT_RECORD_FIRST_ATTRIBUTE_OFFSET+MFT_RECORD_FIRST_ATTRIBUTE_SIZE])[0]
            self.flags = struct.unpack("<H", self.raw_record[MFT_RECORD_FLAGS_OFFSET:MFT_RECORD_FLAGS_OFFSET+MFT_RECORD_FLAGS_SIZE])[0]
            self.size = struct.unpack("<I", self.raw_record[MFT_RECORD_USED_SIZE_OFFSET:MFT_RECORD_USED_SIZE_OFFSET+MFT_RECORD_USED_SIZE_SIZE])[0]
            self.alloc_sizef = struct.unpack("<I", self.raw_record[MFT_RECORD_ALLOCATED_SIZE_OFFSET:MFT_RECORD_ALLOCATED_SIZE_OFFSET+MFT_RECORD_ALLOCATED_SIZE_SIZE])[0]
            self.base_ref = struct.unpack("<Q", self.raw_record[MFT_RECORD_FILE_REFERENCE_OFFSET:MFT_RECORD_FILE_REFERENCE_OFFSET+MFT_RECORD_FILE_REFERENCE_SIZE])[0]
            self.next_attrid = struct.unpack("<H", self.raw_record[MFT_RECORD_NEXT_ATTRIBUTE_ID_OFFSET:MFT_RECORD_NEXT_ATTRIBUTE_ID_OFFSET+MFT_RECORD_NEXT_ATTRIBUTE_ID_SIZE])[0]
            self.recordnum = struct.unpack("<I", self.raw_record[MFT_RECORD_RECORD_NUMBER_OFFSET:MFT_RECORD_RECORD_NUMBER_OFFSET+MFT_RECORD_RECORD_NUMBER_SIZE])[0]
        except struct.error:
            if self.debug:
                print(f"Error parsing MFT record header for record {self.recordnum}")
        
        self.parse_attributes()

    def parse_attributes(self):
        offset = self.attr_off
        while offset < len(self.raw_record) - 8:
            try:
                attr_type = struct.unpack("<L", self.raw_record[offset:offset+4])[0]
                attr_len = struct.unpack("<L", self.raw_record[offset+4:offset+8])[0]

                if attr_type == 0xffffffff or attr_len == 0:
                    break

                self.attribute_types.add(attr_type)

                if attr_type == STANDARD_INFORMATION_ATTRIBUTE:
                    self.parse_si_attribute(offset)
                elif attr_type == FILE_NAME_ATTRIBUTE:
                    self.parse_fn_attribute(offset)
                elif attr_type == ATTRIBUTE_LIST_ATTRIBUTE:
                    self.parse_attribute_list(offset)
                elif attr_type == OBJECT_ID_ATTRIBUTE:
                    self.parse_object_id(offset)
                elif attr_type == SECURITY_DESCRIPTOR_ATTRIBUTE:
                    self.parse_security_descriptor(offset)
                elif attr_type == VOLUME_NAME_ATTRIBUTE:
                    self.parse_volume_name(offset)
                elif attr_type == VOLUME_INFORMATION_ATTRIBUTE:
                    self.parse_volume_information(offset)
                elif attr_type == DATA_ATTRIBUTE:
                    self.parse_data(offset)
                elif attr_type == INDEX_ROOT_ATTRIBUTE:
                    self.parse_index_root(offset)
                elif attr_type == INDEX_ALLOCATION_ATTRIBUTE:
                    self.parse_index_allocation(offset)
                elif attr_type == BITMAP_ATTRIBUTE:
                    self.parse_bitmap(offset)
                elif attr_type == REPARSE_POINT_ATTRIBUTE:
                    self.parse_reparse_point(offset)
                elif attr_type == EA_INFORMATION_ATTRIBUTE:
                    self.parse_ea_information(offset)
                elif attr_type == EA_ATTRIBUTE:
                    self.parse_ea(offset)
                elif attr_type == LOGGED_UTILITY_STREAM_ATTRIBUTE:
                    self.parse_logged_utility_stream(offset)

                offset += attr_len
            except struct.error:
                offset += 1

    def parse_si_attribute(self, offset):
        si_data = self.raw_record[offset+24:offset+72]
        if len(si_data) >= 32:
            try:
                self.si_times = {
                    'crtime': WindowsTime(struct.unpack("<L", si_data[:4])[0], struct.unpack("<L", si_data[4:8])[0]),
                    'mtime': WindowsTime(struct.unpack("<L", si_data[8:12])[0], struct.unpack("<L", si_data[12:16])[0]),
                    'ctime': WindowsTime(struct.unpack("<L", si_data[16:20])[0], struct.unpack("<L", si_data[20:24])[0]),
                    'atime': WindowsTime(struct.unpack("<L", si_data[24:28])[0], struct.unpack("<L", si_data[28:32])[0])
                }
            except struct.error:
                pass

    def parse_fn_attribute(self, offset):
        fn_data = self.raw_record[offset+24:]
        if len(fn_data) >= 64:
            try:
                self.fn_times = {
                    'crtime': WindowsTime(struct.unpack("<L", fn_data[8:12])[0], struct.unpack("<L", fn_data[12:16])[0]),
                    'mtime': WindowsTime(struct.unpack("<L", fn_data[16:20])[0], struct.unpack("<L", fn_data[20:24])[0]),
                    'ctime': WindowsTime(struct.unpack("<L", fn_data[24:28])[0], struct.unpack("<L", fn_data[28:32])[0]),
                    'atime': WindowsTime(struct.unpack("<L", fn_data[32:36])[0], struct.unpack("<L", fn_data[36:40])[0])
                }
                self.filesize = struct.unpack("<Q", fn_data[48:56])[0]
                name_len = struct.unpack("B", fn_data[64:65])[0]
                if len(fn_data) >= 66 + name_len * 2:
                    self.filename = fn_data[66:66+name_len*2].decode('utf-16-le', errors='replace')
                self.parent_ref = struct.unpack("<Q", fn_data[:8])[0] & 0x0000FFFFFFFFFFFF
            except struct.error:
                pass

    def parse_object_id_attribute(self, offset):
        obj_id_data = self.raw_record[offset+24:offset+88]
        if len(obj_id_data) >= 64:
            try:
                self.object_id = str(uuid.UUID(bytes_le=obj_id_data[:16]))
                self.birth_volume_id = str(uuid.UUID(bytes_le=obj_id_data[16:32]))
                self.birth_object_id = str(uuid.UUID(bytes_le=obj_id_data[32:48]))
                self.birth_domain_id = str(uuid.UUID(bytes_le=obj_id_data[48:64]))
            except (struct.error, ValueError):
                if self.debug:
                    print(f"Error parsing Object ID attribute for record {self.recordnum}")
    
    def get_parent_record_num(self):
        return self.parent_ref & 0x0000FFFFFFFFFFFF

    def parse_attribute_list(self, offset):
        pass

    def parse_object_id(self, offset):
        pass

    def parse_security_descriptor(self, offset):
        pass

    def parse_volume_name(self, offset):
        pass

    def parse_volume_information(self, offset):
        pass

    def parse_data(self, offset):
        pass

    def parse_index_root(self, offset):
        pass

    def parse_index_allocation(self, offset):
        pass

    def parse_bitmap(self, offset):
        pass

    def parse_reparse_point(self, offset):
        pass

    def parse_ea_information(self, offset):
        pass

    def parse_ea(self, offset):
        pass

    def parse_logged_utility_stream(self, offset):
        pass

    def to_csv(self):
        row = [
            self.recordnum,
            "Good" if self.magic == int.from_bytes(MFT_RECORD_MAGIC, BYTE_ORDER) else "Bad",
            "Active" if self.flags & FILE_RECORD_IN_USE else "Inactive",
            "Directory" if self.flags & FILE_RECORD_IS_DIRECTORY else "File",
            self.seq,
            self.parent_ref,
            self.base_ref >> 48,  # Parent File Rec. Seq. #
            self.filename,
            self.si_times['crtime'].dtstr,
            self.si_times['mtime'].dtstr,
            self.si_times['atime'].dtstr,
            self.si_times['ctime'].dtstr,
            self.fn_times['crtime'].dtstr,
            self.fn_times['mtime'].dtstr,
            self.fn_times['atime'].dtstr,
            self.fn_times['ctime'].dtstr,
            self.object_id,
            self.birth_volume_id,
            self.birth_object_id,
            self.birth_domain_id,
            "True" if STANDARD_INFORMATION_ATTRIBUTE in self.attribute_types else "False",
            "True" if ATTRIBUTE_LIST_ATTRIBUTE in self.attribute_types else "False",
            "True" if FILE_NAME_ATTRIBUTE in self.attribute_types else "False",
            "True" if VOLUME_NAME_ATTRIBUTE in self.attribute_types else "False",
            "True" if VOLUME_INFORMATION_ATTRIBUTE in self.attribute_types else "False",
            "True" if DATA_ATTRIBUTE in self.attribute_types else "False",
            "True" if INDEX_ROOT_ATTRIBUTE in self.attribute_types else "False",
            "True" if INDEX_ALLOCATION_ATTRIBUTE in self.attribute_types else "False",
            "True" if BITMAP_ATTRIBUTE in self.attribute_types else "False",
            "True" if REPARSE_POINT_ATTRIBUTE in self.attribute_types else "False",
            "True" if EA_INFORMATION_ATTRIBUTE in self.attribute_types else "False",
            "True" if EA_ATTRIBUTE in self.attribute_types else "False",
            "True" if LOGGED_UTILITY_STREAM_ATTRIBUTE in self.attribute_types else "False",
            ""  # Filepath 
        ]
        if self.md5 is not None:
            row.extend([self.md5, self.sha256, self.sha512, self.crc32])
        return row

    def compute_hashes(self):
        md5 = hashlib.md5()
        sha256 = hashlib.sha256()
        sha512 = hashlib.sha512()
        
        md5.update(self.raw_record)
        sha256.update(self.raw_record)
        sha512.update(self.raw_record)
        
        self.md5 = md5.hexdigest()
        self.sha256 = sha256.hexdigest()
        self.sha512 = sha512.hexdigest()
        self.crc32 = format(zlib.crc32(self.raw_record) & 0xFFFFFFFF, '08x')

    def get_file_type(self):
        if self.flags & FILE_RECORD_IS_DIRECTORY:
            return "Directory"
        elif self.flags & FILE_RECORD_IS_EXTENSION:
            return "Extension"
        elif self.flags & FILE_RECORD_HAS_SPECIAL_INDEX:
            return "Special Index"
        else:
            return "File"