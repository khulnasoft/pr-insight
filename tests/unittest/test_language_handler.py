import pytest
from pr_insight.algo.language_handler import sort_files_by_main_languages


class TestSortFilesByMainLanguages:
    """Tests for the sort_files_by_main_languages function"""

    def test_happy_path_sort_files_by_main_languages(self):
        """Test that files are correctly sorted by main language with expected priority"""
        languages = {'Python': 10, 'Java': 5, 'C++': 3}
        files = [
            type('', (object,), {'filename': 'file1.py'})(),
            type('', (object,), {'filename': 'file2.java'})(),
            type('', (object,), {'filename': 'file3.cpp'})(),
            type('', (object,), {'filename': 'file4.py'})(),
            type('', (object,), {'filename': 'file5.py'})()
        ]
        expected_output = [
            {'language': 'Python', 'files': [files[0], files[3], files[4]]},
            {'language': 'Java', 'files': [files[1]]},
            {'language': 'C++', 'files': [files[2]]},
            {'language': 'Other', 'files': []}
        ]
        assert sort_files_by_main_languages(languages, files) == expected_output

    def test_edge_case_empty_languages(self):
        """Test handling of empty languages dictionary"""
        languages = {}
        files = [
            type('', (object,), {'filename': 'file1.py'})(),
            type('', (object,), {'filename': 'file2.java'})()
        ]
        expected_output = [{'language': 'Other', 'files': files}]
        assert sort_files_by_main_languages(languages, files) == expected_output

    def test_edge_case_empty_files(self):
        """Test handling of empty files list"""
        languages = {'Python': 10, 'Java': 5}
        files = []
        expected_output = [{'language': 'Other', 'files': []}]
        assert sort_files_by_main_languages(languages, files) == expected_output

    def test_edge_case_languages_with_no_extensions(self):
        """Test handling of languages with no file extensions"""
        languages = {'Python': 10, 'Java': 5, 'C++': 3}
        files = [
            type('', (object,), {'filename': 'file1.py'})(),
            type('', (object,), {'filename': 'file2.java'})(),
            type('', (object,), {'filename': 'file3.cpp'})()
        ]
        expected_output = [
            {'language': 'Python', 'files': [files[0]]},
            {'language': 'Java', 'files': [files[1]]},
            {'language': 'C++', 'files': [files[2]]},
            {'language': 'Other', 'files': []}
        ]
        assert sort_files_by_main_languages(languages, files) == expected_output

    def test_edge_case_files_with_bad_extensions_only(self):
        """Test handling of files with unsupported extensions and one valid file"""
        languages = {'Python': 10, 'Java': 5, 'C++': 3}
        files = [
            type('', (object,), {'filename': 'file1.csv'})(),
            type('', (object,), {'filename': 'file2.pdf'})(),
            type('', (object,), {'filename': 'file3.py'})()
        ]
        expected_output = [{'language': 'Python', 'files': [files[2]]}, {'language': 'Other', 'files': []}]
        assert sort_files_by_main_languages(languages, files) == expected_output

    def test_general_behaviour_sort_files_by_main_languages(self):
        """Test comprehensive sorting behavior with multiple files and languages"""
        languages = {'Python': 10, 'Java': 5, 'C++': 3}
        files = [
            type('', (object,), {'filename': 'file1.py'})(),
            type('', (object,), {'filename': 'file2.java'})(),
            type('', (object,), {'filename': 'file3.cpp'})(),
            type('', (object,), {'filename': 'file4.py'})(),
            type('', (object,), {'filename': 'file5.py'})(),
            type('', (object,), {'filename': 'file6.py'})(),
            type('', (object,), {'filename': 'file7.java'})(),
            type('', (object,), {'filename': 'file8.cpp'})(),
            type('', (object,), {'filename': 'file9.py'})()
        ]
        expected_output = [
            {'language': 'Python', 'files': [files[0], files[3], files[4], files[5], files[8]]},
            {'language': 'Java', 'files': [files[1], files[6]]},
            {'language': 'C++', 'files': [files[2], files[7]]},
            {'language': 'Other', 'files': []}
        ]
        assert sort_files_by_main_languages(languages, files) == expected_output
