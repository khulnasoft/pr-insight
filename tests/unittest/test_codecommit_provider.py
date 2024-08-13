import pytest
from unittest.mock import patch
from pr_insight.git_providers.codecommit_provider import CodeCommitFile
from pr_insight.git_providers.codecommit_provider import CodeCommitProvider
from pr_insight.git_providers.codecommit_provider import PullRequestCCMimic
from pr_insight.algo.types import EDIT_TYPE, FilePatchInfo


class TestCodeCommitFile:
    # Test that a CodeCommitFile object is created successfully with valid parameters.
    # Generated by KhulnaSoftAI
    def test_valid_parameters(self):
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
    def test_get_title(self):
        # Test that the get_title() function returns the PR title
        with patch.object(CodeCommitProvider, "__init__", lambda x, y: None):
            provider = CodeCommitProvider(None)
            provider.pr = PullRequestCCMimic("My Test PR Title", [])
            assert provider.get_title() == "My Test PR Title"

    def test_get_pr_id(self):
        # Test that the get_pr_id() function returns the correct ID
        with patch.object(CodeCommitProvider, "__init__", lambda x, y: None):
            provider = CodeCommitProvider(None)
            provider.repo_name = "my_test_repo"
            provider.pr_num = 321
            assert provider.get_pr_id() == "my_test_repo/321"

    def test_parse_pr_url(self):
        # Test that the _parse_pr_url() function can extract the repo name and PR number from a CodeCommit URL
        url = "https://us-east-1.console.aws.amazon.com/codesuite/codecommit/repositories/my_test_repo/pull-requests/321"
        repo_name, pr_number = CodeCommitProvider._parse_pr_url(url)
        assert repo_name == "my_test_repo"
        assert pr_number == 321

    def test_is_valid_codecommit_hostname(self):
        # Test the various AWS regions
        assert CodeCommitProvider._is_valid_codecommit_hostname("af-south-1.console.aws.amazon.com")
        assert CodeCommitProvider._is_valid_codecommit_hostname("ap-east-1.console.aws.amazon.com")
        assert CodeCommitProvider._is_valid_codecommit_hostname("ap-northeast-1.console.aws.amazon.com")
        assert CodeCommitProvider._is_valid_codecommit_hostname("ap-northeast-2.console.aws.amazon.com")
        assert CodeCommitProvider._is_valid_codecommit_hostname("ap-northeast-3.console.aws.amazon.com")
        assert CodeCommitProvider._is_valid_codecommit_hostname("ap-south-1.console.aws.amazon.com")
        assert CodeCommitProvider._is_valid_codecommit_hostname("ap-south-2.console.aws.amazon.com")
        assert CodeCommitProvider._is_valid_codecommit_hostname("ap-southeast-1.console.aws.amazon.com")
        assert CodeCommitProvider._is_valid_codecommit_hostname("ap-southeast-2.console.aws.amazon.com")
        assert CodeCommitProvider._is_valid_codecommit_hostname("ap-southeast-3.console.aws.amazon.com")
        assert CodeCommitProvider._is_valid_codecommit_hostname("ap-southeast-4.console.aws.amazon.com")
        assert CodeCommitProvider._is_valid_codecommit_hostname("ca-central-1.console.aws.amazon.com")
        assert CodeCommitProvider._is_valid_codecommit_hostname("eu-central-1.console.aws.amazon.com")
        assert CodeCommitProvider._is_valid_codecommit_hostname("eu-central-2.console.aws.amazon.com")
        assert CodeCommitProvider._is_valid_codecommit_hostname("eu-north-1.console.aws.amazon.com")
        assert CodeCommitProvider._is_valid_codecommit_hostname("eu-south-1.console.aws.amazon.com")
        assert CodeCommitProvider._is_valid_codecommit_hostname("eu-south-2.console.aws.amazon.com")
        assert CodeCommitProvider._is_valid_codecommit_hostname("eu-west-1.console.aws.amazon.com")
        assert CodeCommitProvider._is_valid_codecommit_hostname("eu-west-2.console.aws.amazon.com")
        assert CodeCommitProvider._is_valid_codecommit_hostname("eu-west-3.console.aws.amazon.com")
        assert CodeCommitProvider._is_valid_codecommit_hostname("il-central-1.console.aws.amazon.com")
        assert CodeCommitProvider._is_valid_codecommit_hostname("me-central-1.console.aws.amazon.com")
        assert CodeCommitProvider._is_valid_codecommit_hostname("me-south-1.console.aws.amazon.com")
        assert CodeCommitProvider._is_valid_codecommit_hostname("sa-east-1.console.aws.amazon.com")
        assert CodeCommitProvider._is_valid_codecommit_hostname("us-east-1.console.aws.amazon.com")
        assert CodeCommitProvider._is_valid_codecommit_hostname("us-east-2.console.aws.amazon.com")
        assert CodeCommitProvider._is_valid_codecommit_hostname("us-gov-east-1.console.aws.amazon.com")
        assert CodeCommitProvider._is_valid_codecommit_hostname("us-gov-west-1.console.aws.amazon.com")
        assert CodeCommitProvider._is_valid_codecommit_hostname("us-west-1.console.aws.amazon.com")
        assert CodeCommitProvider._is_valid_codecommit_hostname("us-west-2.console.aws.amazon.com")
        # Test non-AWS regions
        assert not CodeCommitProvider._is_valid_codecommit_hostname("no-such-region.console.aws.amazon.com")
        assert not CodeCommitProvider._is_valid_codecommit_hostname("console.aws.amazon.com")

    # Test that an error is raised when an invalid CodeCommit URL is provided to the set_pr() method of the CodeCommitProvider class.
    # Generated by KhulnaSoftAI
    def test_invalid_codecommit_url(self):
        provider = CodeCommitProvider()
        with pytest.raises(ValueError):
            provider.set_pr("https://example.com/codecommit/repositories/my_test_repo/pull-requests/4321")

    def test_get_file_extensions(self):
        filenames = [
            "app.py",
            "cli.py",
            "composer.json",
            "composer.lock",
            "hello.py",
            "image1.jpg",
            "image2.JPG",
            "index.js",
            "provider.py",
            "README",
            "test.py",
        ]
        expected_extensions = [
            ".py",
            ".py",
            ".json",
            ".lock",
            ".py",
            ".jpg",
            ".jpg",
            ".js",
            ".py",
            "",
            ".py",
        ]
        extensions = CodeCommitProvider._get_file_extensions(filenames)
        assert extensions == expected_extensions

    def test_get_language_percentages(self):
        extensions = [
            ".py",
            ".py",
            ".json",
            ".lock",
            ".py",
            ".jpg",
            ".jpg",
            ".js",
            ".py",
            "",
            ".py",
        ]
        percentages = CodeCommitProvider._get_language_percentages(extensions)
        assert percentages[".py"] == 45
        assert percentages[".json"] == 9
        assert percentages[".lock"] == 9
        assert percentages[".jpg"] == 18
        assert percentages[".js"] == 9
        assert percentages[""] == 9

        # The _get_file_extensions function needs the "." prefix on the extension,
        # but the _get_language_percentages function will work with or without the "." prefix
        extensions = [
            "txt",
            "py",
            "py",
        ]
        percentages = CodeCommitProvider._get_language_percentages(extensions)
        assert percentages["py"] == 67
        assert percentages["txt"] == 33

        # test an empty list
        percentages = CodeCommitProvider._get_language_percentages([])
        assert percentages == {}

    def test_get_edit_type(self):
        # Test that the _get_edit_type() function can convert a CodeCommit letter to an EDIT_TYPE enum
        assert CodeCommitProvider._get_edit_type("A") == EDIT_TYPE.ADDED
        assert CodeCommitProvider._get_edit_type("D") == EDIT_TYPE.DELETED
        assert CodeCommitProvider._get_edit_type("M") == EDIT_TYPE.MODIFIED
        assert CodeCommitProvider._get_edit_type("R") == EDIT_TYPE.RENAMED

        assert CodeCommitProvider._get_edit_type("a") == EDIT_TYPE.ADDED
        assert CodeCommitProvider._get_edit_type("d") == EDIT_TYPE.DELETED
        assert CodeCommitProvider._get_edit_type("m") == EDIT_TYPE.MODIFIED
        assert CodeCommitProvider._get_edit_type("r") == EDIT_TYPE.RENAMED

        assert CodeCommitProvider._get_edit_type("X") is None

    def test_add_additional_newlines(self):
        # a short string to test adding double newlines
        input = "abc\ndef\n\n___\nghi\njkl\nmno\n\npqr\n"
        expect = "abc\n\ndef\n\n___\n\nghi\n\njkl\n\nmno\n\npqr\n\n"
        assert CodeCommitProvider._add_additional_newlines(input) == expect
        # a test example from a real PR
        input = "## PR Type:\nEnhancement\n\n___\n## PR Description:\nThis PR introduces a new feature to the script, allowing users to filter servers by name.\n\n___\n## PR Main Files Walkthrough:\n`foo`: The foo script has been updated to include a new command line option `-f` or `--filter`.\n`bar`: The bar script has been updated to list stopped servers.\n"
        expect = "## PR Type:\n\nEnhancement\n\n___\n\n## PR Description:\n\nThis PR introduces a new feature to the script, allowing users to filter servers by name.\n\n___\n\n## PR Main Files Walkthrough:\n\n`foo`: The foo script has been updated to include a new command line option `-f` or `--filter`.\n\n`bar`: The bar script has been updated to list stopped servers.\n\n"
        assert CodeCommitProvider._add_additional_newlines(input) == expect

    def test_remove_markdown_html(self):
        input = "## PR Feedback\n<details><summary>Code feedback:</summary>\nfile foo\n</summary>\n"
        expect = "## PR Feedback\nCode feedback:\nfile foo\n\n"
        assert CodeCommitProvider._remove_markdown_html(input) == expect
