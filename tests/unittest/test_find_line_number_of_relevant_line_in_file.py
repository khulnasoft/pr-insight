import pytest
from pr_insight.algo.types import FilePatchInfo
from pr_insight.algo.utils import find_line_number_of_relevant_line_in_file


class TestFindLineNumberOfRelevantLineInFile:
    """Tests for the find_line_number_of_relevant_line_in_file function"""

    def test_happy_path_line_found_in_patch(self):
        """Test that correct line number and position are returned when line is found in patch"""
        diff_files = [
            FilePatchInfo(base_file='file1', head_file='file1', 
                         patch='@@ -1,1 +1,2 @@\n-line1\n+line2\n+relevant_line\n', 
                         filename='file1')
        ]
        relevant_file = 'file1'
        relevant_line = 'relevant_line'
        expected = (3, 2)  # (position in patch, absolute position in new file)

        result = find_line_number_of_relevant_line_in_file(diff_files, relevant_file, relevant_line)

        assert result == expected

    def test_similar_line_found_with_difflib(self):
        """Test that correct line number and position are returned for similar line match"""
        diff_files = [
            FilePatchInfo(base_file='file1', head_file='file1',
                         patch='@@ -1,1 +1,2 @@\n-line1\n+relevant_line in file similar match\n',
                         filename='file1')
        ]
        relevant_file = 'file1'
        relevant_line = '+relevant_line in file similar match '  # Extra space to test difflib matching
        expected = (2, 1)

        result = find_line_number_of_relevant_line_in_file(diff_files, relevant_file, relevant_line)

        assert result == expected

    def test_line_not_found(self):
        """Test that (-1, -1) is returned when line is not found in patch or via difflib"""
        diff_files = [
            FilePatchInfo(base_file='file1', head_file='file1',
                         patch='@@ -1,1 +1,2 @@\n-line1\n+relevant_line\n',
                         filename='file1')
        ]
        relevant_file = 'file1'
        relevant_line = 'not_found'
        expected = (-1, -1)

        result = find_line_number_of_relevant_line_in_file(diff_files, relevant_file, relevant_line)

        assert result == expected

    def test_file_not_found(self):
        """Test that (-1, -1) is returned when file is not found in patches"""
        diff_files = [
            FilePatchInfo(base_file='file2', head_file='file2',
                         patch='@@ -1,1 +1,2 @@\n-line1\n+relevant_line\n',
                         filename='file2')
        ]
        relevant_file = 'file1'
        relevant_line = 'relevant_line'
        expected = (-1, -1)

        result = find_line_number_of_relevant_line_in_file(diff_files, relevant_file, relevant_line)

        assert result == expected

    def test_empty_line(self):
        """Test handling of empty relevant line"""
        diff_files = [
            FilePatchInfo(base_file='file1', head_file='file1',
                         patch='@@ -1,1 +1,2 @@\n-line1\n+relevant_line\n',
                         filename='file1')
        ]
        relevant_file = 'file1'
        relevant_line = ''
        expected = (0, 0)

        result = find_line_number_of_relevant_line_in_file(diff_files, relevant_file, relevant_line)

        assert result == expected

    def test_line_found_but_deleted(self):
        """Test that (-1, -1) is returned when line is found but was deleted"""
        diff_files = [
            FilePatchInfo(base_file='file1', head_file='file1',
                         patch='@@ -1,2 +1,1 @@\n-line1\n-relevant_line\n',
                         filename='file1')
        ]
        relevant_file = 'file1'
        relevant_line = 'relevant_line'
        expected = (-1, -1)

        result = find_line_number_of_relevant_line_in_file(diff_files, relevant_file, relevant_line)

        assert result == expected