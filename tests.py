import os
import unittest
import datetime
import tempfile
from xp3 import XP3, XP3Reader, XP3Writer
from structs.game_list import game_list
from encrypt.encrypt_interface import EncryptInterface

class Encryption(unittest.TestCase):
    """Encryption test with Numpy and pure Python XORing"""

    def encrypt_and_decrypt(self, data, game_name, use_numpy, encrypt_instance: EncryptInterface):
        with XP3Writer(silent=True, use_numpy=use_numpy, game_name=game_name, encrypt_instance=encrypt_instance) as xp3:
            xp3.add('dummy_file', data)
            archive = xp3.pack_up()

        with XP3Reader(archive, silent=True, use_numpy=use_numpy) as xp3:
            self.assertEqual(xp3.is_encrypted, game_name != 'none')
            file = xp3.open('dummy_file')
            self.assertEqual(file.is_encrypted, game_name != 'none')
            self.assertEqual('dummy_file', file.file_path)
            self.assertEqual(data, file.read(encryption_type=game_name, encrypt_instance=encrypt_instance))

    def with_numpy(self, data):
        # Crash test early if Numpy is not present
        import numpy
        del numpy
        for game_name in game_list:
            crypt_class, params, _,  = game_list[game_name]
            encrypt_instance = crypt_class(**params)
            print(f'Testing {game_name} with numpy')
            self.encrypt_and_decrypt(data, game_name, True, encrypt_instance)

    def with_python(self, data):
        for game_name in game_list:
            crypt_class, params, _,  = game_list[game_name]
            encrypt_instance = crypt_class(**params)
            print(f'Testing {game_name} without numpy')
            self.encrypt_and_decrypt(data, game_name, False, encrypt_instance)

    def test_numpy_uncompressed(self):
        self.with_numpy(b'dummy_data')

    def test_numpy_compressed(self):
        self.with_numpy(b'111111111111')

    def test_python_uncompressed(self):
        self.with_python(b'dummy_data')

    def test_python_compressed(self):
        self.with_python(b'111111111111')


class FolderReadAndWrite(unittest.TestCase):
    """Read and write from and into file"""

    dummy_data = (
        ('dummyfile1', b'dummydata1'),
        ('dummyfile2', b'dummydata2')
    )

    def test(self):
        with tempfile.TemporaryDirectory() as datadir, tempfile.TemporaryDirectory() as xp3dir:
            for filename, filedata in self.dummy_data:
                with open(os.path.join(datadir, filename), 'wb') as file:
                    file.write(filedata)

            xp3_path = os.path.join(xp3dir, 'data.xp3')
            with XP3(xp3_path, mode='w', silent=True) as xp3:
                xp3.add_folder(datadir)

            with XP3(xp3_path, mode='r', silent=True) as xp3:
                file1 = xp3.open('dummyfile1')
                file2 = xp3.open('dummyfile2')
                file1_name, file1_data = self.dummy_data[0]
                file2_name, file2_data = self.dummy_data[1]
                self.assertEqual(file1_name, file1.file_path)
                self.assertEqual(file2_name, file2.file_path)
                self.assertEqual(file1_data, file1.read())
                self.assertEqual(file2_data, file2.read())
                xp3.extract(os.path.join(xp3dir, 'out'))  # Extract the archive to folder
                xp3.file_index.extract(os.path.join(xp3dir, 'data.xp3.index'))  # Dump file index

            # Check the extracted files
            for filename, filedata in self.dummy_data:
                with open(os.path.join(xp3dir, 'out', filename), 'rb') as file:
                    self.assertEqual(filedata, file.read())


class MemoryReadAndWrite(unittest.TestCase):
    """In memory read and write"""  ## modified, never compress
    dummy_data = (
        ('dummy_file_1', b'dummydata1', round(datetime.datetime.utcnow().timestamp() * 1000), False),  # convert timestamp to milliseconds
        ('dummy_file_2', b'dummydata2', 2000, False),
        ('dummy_file_3', b'111111111111', 3000, False),  # should be compressed
        ('dummy_file_4', b'11111111111', 3000, False)  # FUCK!! compressed and uncompressed sizes should match, do not compress
    )

    def test(self):
        with XP3Writer(silent=True) as xp3:
            for filepath, data, timestamp, compressed in self.dummy_data:
                xp3.add(filepath, data, timestamp=timestamp)
            archive = xp3.pack_up()

        with XP3Reader(archive, silent=True) as xp3:

            for index, (filepath, data, timestamp, compressed) in enumerate(self.dummy_data):
                file = xp3.open(index)
                self.assertEqual(filepath, file.file_path)
                self.assertEqual(data, file.read())
                self.assertEqual(timestamp // 1000, file.time.timestamp)
                self.assertEqual(compressed, file.segm.segments[0].is_compressed)


class DuplicateWrite(unittest.TestCase):
    """Make sure that duplicates can not be added into archive"""

    def test(self):
        with XP3Writer(silent=True) as xp3:
            xp3.add('duplicate_file', b'12345')
            with self.assertRaises(FileExistsError):
                xp3.add('duplicate_file', b'12345')


if __name__ == '__main__':
    unittest.main()
