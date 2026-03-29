from infracheck.parsers.terraform import parse_directory


def test_parse_directory_returns_resources():
    resources = parse_directory("tests/fixtures")

    assert "aws_sqs_queue" in resources
    assert "aws_lambda_function" in resources


def test_sqs_queue_fields():
    resources = parse_directory("tests/fixtures")
    queue = resources["aws_sqs_queue"][0]

    assert queue["_name"] == "my_queue"
    assert queue["name"] == "my-queue"


def test_lambda_function_fields():
    resources = parse_directory("tests/fixtures")
    func = resources["aws_lambda_function"][0]

    assert func["_name"] == "my_func"
    assert func["function_name"] == "my-func"


def test_empty_directory_returns_empty_dict(tmp_path):
    resources = parse_directory(str(tmp_path))

    assert resources == {}


def test_invalid_tf_file_is_skipped(tmp_path):
    bad_file = tmp_path / "broken.tf"
    bad_file.write_text("this is not valid hcl {{{")

    resources = parse_directory(str(tmp_path))

    assert resources == {}
