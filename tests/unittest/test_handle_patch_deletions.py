import pytest
from pr_insight.algo.git_patch_processing import handle_patch_deletions


class TestHandlePatchDeletions:
    """Tests for the handle_patch_deletions function"""

    def test_happy_path_with_content(self):
        """Test that original patch is returned when new file content exists"""
        patch = '--- a/file.py\n+++ b/file.py\n@@ -1,2 +1,2 @@\n-foo\n-bar\n+baz\n'
        original_content = 'foo\nbar\n'
        new_content = 'foo\nbaz\n'
        file_name = 'file.py'

        result = handle_patch_deletions(patch, original_content, new_content, file_name)
        
        assert result == patch.rstrip()

    def test_empty_new_content(self):
        """Test that None is returned when new file content is empty (file deleted)"""
        patch = '--- a/file.py\n+++ b/file.py\n@@ -1,2 +1,2 @@\n-foo\n-bar\n'
        original_content = 'foo\nbar\n'
        new_content = ''
        file_name = 'file.py'

        result = handle_patch_deletions(patch, original_content, new_content, file_name)
        
        assert result is None

    def test_identical_content(self):
        """Test that original patch is returned when file content hasn't changed"""
        patch = '--- a/file.py\n+++ b/file.py\n@@ -1,2 +1,2 @@\n-foo\n-bar\n'
        original_content = 'foo\nbar\n'
        new_content = 'foo\nbar\n'
        file_name = 'file.py'

        result = handle_patch_deletions(patch, original_content, new_content, file_name)
        
        assert result == patch.rstrip()

    def test_modified_content(self):
        """Test that modified patch is returned when content has changed"""
        patch = '--- a/file.py\n+++ b/file.py\n@@ -1,2 +1,2 @@\n-foo\n-bar\n'
        original_content = 'foo\nbar\n'
        new_content = 'foo\nbaz\n'
        file_name = 'file.py'
        expected_patch = '--- a/file.py\n+++ b/file.py\n@@ -1,2 +1,2 @@\n-foo\n-bar'

        result = handle_patch_deletions(patch, original_content, new_content, file_name)
        
        assert result == expected_patch
