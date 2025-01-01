import pytest
from unittest.mock import patch
from pr_insight.git_providers.codecommit_provider import CodeCommitFile
from pr_insight.git_providers.codecommit_provider import CodeCommitProvider
from pr_insight.git_providers.codecommit_provider import PullRequestCCMimic
from pr_insight.algo.types import EDIT_TYPE, FilePatchInfo


class TestCodeCommitFile:
    def test_valid_parameters(self):
        """Test that a CodeCommitFile object is created successfully with valid parameters"""
        a_path = "path/to/file_a"
        a_blob_id = "12345"
        b_path = "path/to/file_b"
        b_blob_id = "67890"
        edit_type = EDIT_TYPE.ADDED

        file = CodeCommitFile(a_path, a_blob_id, b_path, b_blob_id, edit_type)

        assert file.a_path == a_path
        assert file.a_blob_id == a_blob_id
        assert file.b_path == b_path
        assert file.b_blob_id == b_blob_id
        assert file.edit_type == edit_type
        assert file.filename == b_path


class TestCodeCommitProvider:
    @patch.object(CodeCommitProvider, "__init__", lambda x, y: None)
    def test_get_title(self):
        """Test that get_title() returns the PR title"""
        provider = CodeCommitProvider(None)
        provider.pr = PullRequestCCMimic("My Test PR Title", [])
        assert provider.get_title() == "My Test PR Title"

    @patch.object(CodeCommitProvider, "__init__", lambda x, y: None) 
    def test_get_pr_id(self):
        """Test that get_pr_id() returns the correct ID"""
        provider = CodeCommitProvider(None)
        provider.repo_name = "my_test_repo"
        provider.pr_num = 321
        assert provider.get_pr_id() == "my_test_repo/321"

    def test_parse_pr_url(self):
        """Test that _parse_pr_url() extracts repo name and PR number from CodeCommit URL"""
        url = "https://us-east-1.console.aws.amazon.com/codesuite/codecommit/repositories/my_test_repo/pull-requests/321"
        repo_name, pr_number = CodeCommitProvider._parse_pr_url(url)
        assert repo_name == "my_test_repo"
        assert pr_number == 321

    def test_is_valid_codecommit_hostname(self):
        """Test validation of AWS region hostnames"""
        # Valid AWS regions
        valid_regions = [
            "af-south-1", "ap-east-1", "ap-northeast-1", "ap-northeast-2", "ap-northeast-3",
            "ap-south-1", "ap-south-2", "ap-southeast-1", "ap-southeast-2", "ap-southeast-3",
            "ap-southeast-4", "ca-central-1", "eu-central-1", "eu-central-2", "eu-north-1",
            "eu-south-1", "eu-south-2", "eu-west-1", "eu-west-2", "eu-west-3",
            "il-central-1", "me-central-1", "me-south-1", "sa-east-1", "us-east-1",
            "us-east-2", "us-gov-east-1", "us-gov-west-1", "us-west-1", "us-west-2"
        ]
        
        for region in valid_regions:
            assert CodeCommitProvider._is_valid_codecommit_hostname(f"{region}.console.aws.amazon.com")

        # Invalid hostnames
        assert not CodeCommitProvider._is_valid_codecommit_hostname("no-such-region.console.aws.amazon.com")
        assert not CodeCommitProvider._is_valid_codecommit_hostname("console.aws.amazon.com")

    def test_invalid_codecommit_url(self):
        """Test that set_pr() raises ValueError for invalid CodeCommit URL"""
        provider = CodeCommitProvider()
        with pytest.raises(ValueError):
            provider.set_pr("https://example.com/codecommit/repositories/my_test_repo/pull-requests/4321")

    def test_get_file_extensions(self):
        """Test extraction of file extensions"""
        filenames = [
            "app.py", "cli.py", "composer.json", "composer.lock",
            "hello.py", "image1.jpg", "image2.JPG", "index.js",
            "provider.py", "README", "test.py"
        ]
        expected_extensions = [
            ".py", ".py", ".json", ".lock", ".py", ".jpg", ".jpg",
            ".js", ".py", "", ".py"
        ]
        extensions = CodeCommitProvider._get_file_extensions(filenames)
        assert extensions == expected_extensions

    def test_get_language_percentages(self):
        """Test calculation of language percentages"""
        # Test with dot prefix
        extensions = [
            ".py", ".py", ".json", ".lock", ".py", ".jpg", ".jpg",
            ".js", ".py", "", ".py"
        ]
        percentages = CodeCommitProvider._get_language_percentages(extensions)
        assert percentages[".py"] == 45
        assert percentages[".json"] == 9
        assert percentages[".lock"] == 9
        assert percentages[".jpg"] == 18
        assert percentages[".js"] == 9
        assert percentages[""] == 9

        # Test without dot prefix
        extensions = ["txt", "py", "py"]
        percentages = CodeCommitProvider._get_language_percentages(extensions)
        assert percentages["py"] == 67
        assert percentages["txt"] == 33

        # Test empty list
        assert CodeCommitProvider._get_language_percentages([]) == {}

    def test_get_edit_type(self):
        """Test conversion of CodeCommit edit types to EDIT_TYPE enum"""
        # Test uppercase letters
        assert CodeCommitProvider._get_edit_type("A") == EDIT_TYPE.ADDED
        assert CodeCommitProvider._get_edit_type("D") == EDIT_TYPE.DELETED
        assert CodeCommitProvider._get_edit_type("M") == EDIT_TYPE.MODIFIED
        assert CodeCommitProvider._get_edit_type("R") == EDIT_TYPE.RENAMED

        # Test lowercase letters
        assert CodeCommitProvider._get_edit_type("a") == EDIT_TYPE.ADDED
        assert CodeCommitProvider._get_edit_type("d") == EDIT_TYPE.DELETED
        assert CodeCommitProvider._get_edit_type("m") == EDIT_TYPE.MODIFIED
        assert CodeCommitProvider._get_edit_type("r") == EDIT_TYPE.RENAMED

        # Test invalid type
        assert CodeCommitProvider._get_edit_type("X") is None

    def test_add_additional_newlines(self):
        """Test addition of extra newlines for formatting"""
        # Simple test case
        input_str = "abc\ndef\n\n___\nghi\njkl\nmno\n\npqr\n"
        expected = "abc\n\ndef\n\n___\n\nghi\n\njkl\n\nmno\n\npqr\n\n"
        assert CodeCommitProvider._add_additional_newlines(input_str) == expected

        # Complex PR example
        input_str = (
            "## PR Type:\nEnhancement\n\n___\n"
            "## PR Description:\nThis PR introduces a new feature to the script, allowing users to filter servers by name.\n\n___\n"
            "## PR Main Files Walkthrough:\n`foo`: The foo script has been updated to include a new command line option `-f` or `--filter`.\n"
            "`bar`: The bar script has been updated to list stopped servers.\n"
        )
        expected = (
            "## PR Type:\n\nEnhancement\n\n___\n\n"
            "## PR Description:\n\nThis PR introduces a new feature to the script, allowing users to filter servers by name.\n\n___\n\n"
            "## PR Main Files Walkthrough:\n\n`foo`: The foo script has been updated to include a new command line option `-f` or `--filter`.\n\n"
            "`bar`: The bar script has been updated to list stopped servers.\n\n"
        )
        assert CodeCommitProvider._add_additional_newlines(input_str) == expected

    def test_remove_markdown_html(self):
        """Test removal of markdown and HTML tags"""
        input_str = "## PR Feedback\n<details><summary>Code feedback:</summary>\nfile foo\n</summary>\n"
        expected = "## PR Feedback\nCode feedback:\nfile foo\n\n"
        assert CodeCommitProvider._remove_markdown_html(input_str) == expected
