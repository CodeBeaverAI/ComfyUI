import os
import sys
import enum
import tempfile
import pytest
import importlib
import shutil
import argparse

# Import the module under test and its dependencies
import comfy.cli_args as cli_args
import comfy.options


def test_default_values():
    """Test that default values are set correctly when no extra command line arguments are provided."""
    # Using the parser directly (this does not trigger the post-processing which is done
    # in the module-level code; defaults come from parse_args([]) if comfy.options.args_parsing is False).
    args = cli_args.parser.parse_args([])
    assert args.listen == "127.0.0.1"
    assert args.port == 8188
    # For a few options that are not provided, verify they hold their default values.
    assert args.tls_keyfile is None
    assert args.tls_certfile is None
    assert args.enable_cors_header is None
    assert args.max_upload_size == 100


def test_enum_action_preview_method_valid():
    """Test that a valid value for --preview-method is correctly converted to an Enum."""
    args = cli_args.parser.parse_args(["--preview-method", "latent2rgb"])
    # The __call__ method in EnumAction should convert the string argument.
    assert args.preview_method == cli_args.LatentPreviewMethod.Latent2RGB


def test_enum_action_preview_method_invalid():
    """Test that an invalid value for --preview-method causes an error."""
    with pytest.raises(SystemExit):
        cli_args.parser.parse_args(["--preview-method", "invalid_value"])


def test_is_valid_directory_none():
    """Test that is_valid_directory returns None when passed None."""
    result = cli_args.is_valid_directory(None)
    assert result is None


def test_is_valid_directory_valid(tmp_path):
    """Test that is_valid_directory returns the directory path when a valid directory is provided."""
    valid_dir = str(tmp_path)
    result = cli_args.is_valid_directory(valid_dir)
    assert result == valid_dir


def test_is_valid_directory_invalid(tmp_path):
    """Test that is_valid_directory raises an error when given a non-directory path."""
    # Create a temporary file, not a directory.
    temp_file = tmp_path / "temp.txt"
    temp_file.write_text("dummy content")
    with pytest.raises(argparse.ArgumentTypeError):
        cli_args.is_valid_directory(str(temp_file))


def test_fast_no_arguments():
    """Test that when --fast is provided with no extra arguments, all performance features are enabled."""
    args = cli_args.parser.parse_args(["--fast"])
    # Because nargs="*" returns an empty list when no arguments are provided
    # the post-processing code sets fast to set(PerformanceFeature).
    # Simulate the post-processing manually:
    if args.fast is None:
        args.fast = set()
    elif args.fast == []:
        args.fast = set(cli_args.PerformanceFeature)
    else:
        args.fast = set(args.fast)
    # Verify that all performance features are included.
    expected = set(cli_args.PerformanceFeature)
    assert args.fast == expected


def test_fast_specific_argument():
    """Test that when --fast is provided with a specific performance optimization the fast set only contains that feature."""
    args = cli_args.parser.parse_args(["--fast", "fp16_accumulation"])
    # Simulate the post-processing logic
    if args.fast is None:
        args.fast = set()
    elif args.fast == []:
        args.fast = set(cli_args.PerformanceFeature)
    else:
        args.fast = set(args.fast)
    expected = {cli_args.PerformanceFeature.Fp16Accumulation}
    assert args.fast == expected


def test_mutually_exclusive_cuda_args():
    """Test that providing conflicting cuda options (e.g. --cuda-malloc and --disable-cuda-malloc) causes an error."""
    with pytest.raises(SystemExit):
        cli_args.parser.parse_args(["--cuda-malloc", "--disable-cuda-malloc"])


def test_post_processing_windows_standalone_build_auto_launch(monkeypatch):
    """Test that --windows-standalone-build sets auto_launch to True,
    and that --disable-auto-launch can override it.
    This test reloads the cli_args module to trigger the module‐level post‐processing code."""
    # Backup original sys.argv and comfy.options.args_parsing value
    original_argv = sys.argv[:]
    original_args_parsing = comfy.options.args_parsing

    try:
        comfy.options.args_parsing = True
        # Test case: only --windows-standalone-build provided
        test_args = ["dummy", "--windows-standalone-build"]
        monkeypatch.setattr(sys, "argv", test_args)
        importlib.reload(cli_args)
        assert cli_args.args.auto_launch is True

        # Test case: both --windows-standalone-build and --disable-auto-launch provided, latter wins.
        test_args = ["dummy", "--windows-standalone-build", "--disable-auto-launch"]
        monkeypatch.setattr(sys, "argv", test_args)
        importlib.reload(cli_args)
        assert cli_args.args.auto_launch is False
    finally:
        sys.argv = original_argv
        comfy.options.args_parsing = original_args_parsing


def test_post_processing_force_fp16(monkeypatch):
    """Test that --force-fp16 sets fp16_unet to True through post-processing."""
    original_argv = sys.argv[:]
    original_args_parsing = comfy.options.args_parsing

    try:
        comfy.options.args_parsing = True
        test_args = ["dummy", "--force-fp16"]
        monkeypatch.setattr(sys, "argv", test_args)
        importlib.reload(cli_args)
        assert cli_args.args.fp16_unet is True
    finally:
        sys.argv = original_argv
        comfy.options.args_parsing = original_args_parsing

# End of tests for cli_args
def test_enable_cors_header_no_argument():
    """Test that --enable-cors-header with no argument uses the default const '*'."""
    args = cli_args.parser.parse_args(["--enable-cors-header"])
    assert args.enable_cors_header == "*"

def test_enable_cors_header_with_argument():
    """Test that --enable-cors-header with a provided origin returns that origin."""
    args = cli_args.parser.parse_args(["--enable-cors-header", "https://example.com"])
    assert args.enable_cors_header == "https://example.com"

def test_extra_model_paths_config_multiple():
    """Test that multiple --extra-model-paths-config options are aggregated properly.
    Since the action is "append" with nargs="+", the value is a list of lists."""
    args = cli_args.parser.parse_args(["--extra-model-paths-config", "path1", "path2", "--extra-model-paths-config", "path3"])
    assert args.extra_model_paths_config == [["path1", "path2"], ["path3"]]

def test_directml_no_argument():
    """Test that --directml provided with no argument defaults to -1."""
    args = cli_args.parser.parse_args(["--directml"])
    assert args.directml == -1

def test_directml_with_argument():
    """Test that --directml provided with a specific argument returns that value."""
    args = cli_args.parser.parse_args(["--directml", "2"])
    assert args.directml == 2

def test_force_channels_last():
    """Test that --force-channels-last sets its flag to True."""
    args = cli_args.parser.parse_args(["--force-channels-last"])
    assert args.force_channels_last is True

def test_deterministic_argument():
    """Test that --deterministic sets the deterministic flag to True."""
    args = cli_args.parser.parse_args(["--deterministic"])
    assert args.deterministic is True

def test_default_hashing_function():
    """Test that --default-hashing-function uses its default and can be overridden."""
    # Without specifying, the default should be sha256.
    args = cli_args.parser.parse_args([])
    assert args.default_hashing_function == "sha256"
    # Now override the default.
    args2 = cli_args.parser.parse_args(["--default-hashing-function", "md5"])
    assert args2.default_hashing_function == "md5"

def test_oneapi_device_selector():
    """Test that --oneapi-device-selector accepts a valid selector string."""
    args = cli_args.parser.parse_args(["--oneapi-device-selector", "selector_string"])
    assert args.oneapi_device_selector == "selector_string"

def test_cuda_device_argument():
    """Test that --cuda-device argument is parsed correctly as a string."""
    args = cli_args.parser.parse_args(["--cuda-device", "cuda:0"])
    assert args.cuda_device == "cuda:0"

def test_mutually_exclusive_cache_args():
    """Test that providing both --cache-classic and --cache-lru leads to an error."""
    with pytest.raises(SystemExit):
            cli_args.parser.parse_args(["--cache-classic", "--cache-lru", "10"])

def test_disable_xformers():
    """Test that --disable-xformers flag sets its value to True."""
    args = cli_args.parser.parse_args(["--disable-xformers"])
    assert args.disable_xformers is True

def test_verbose_no_argument():
    """Test that --verbose with no argument sets logging level to 'DEBUG' (using the const)."""
    args = cli_args.parser.parse_args(["--verbose"])
    assert args.verbose == "DEBUG"