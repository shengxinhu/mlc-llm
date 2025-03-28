"""Command line entrypoint of weight conversion."""

import argparse
from pathlib import Path
from typing import Union

from mlc_llm.interface.convert_weight import convert_weight
from mlc_llm.interface.help import HELP
from mlc_llm.model import MODELS
from mlc_llm.quantization import QUANTIZATION
from mlc_llm.support.argparse import ArgumentParser
from mlc_llm.support.auto_config import detect_config, detect_model_type
from mlc_llm.support.auto_device import detect_device
from mlc_llm.support.auto_weight import detect_weight


def main(argv):
    """Parse command line argumennts and apply quantization."""

    def _parse_source(path: Union[str, Path], config_path: Path) -> Path:
        if path == "auto":
            return config_path.parent
        path = Path(path)
        if not path.exists():
            raise argparse.ArgumentTypeError(f"Model source does not exist: {path}")
        return path

    def _parse_output(path: Union[str, Path]) -> Path:
        path = Path(path)
        if not path.is_dir():
            path.mkdir(parents=True, exist_ok=True)
        return path
    
    class LoRAPathAction(argparse.Action):
        def parse_path(self, path: Union[str, Path]) -> Path:
            path = Path(path)
            if not path.exists():
                raise argparse.ArgumentTypeError(f"Model source does not exist: {path}")
            return path

        def __call__(self, parser, namespace, values, option_string=None):
            setattr(namespace, self.dest, {})
            for lora_path in values:
                if "=" in lora_path:
                    name, path = lora_path.split("=", 1)
                    getattr(namespace, self.dest)[name] = self.parse_path(path)
                else:
                    getattr(namespace, self.dest)[lora_path] = self.parse_path(lora_path)

    parser = ArgumentParser("MLC AutoLLM Quantization Framework")
    parser.add_argument(
        "config",
        type=detect_config,
        help=HELP["config"] + " (required)",
    )
    parser.add_argument(
        "--quantization",
        type=str,
        required=True,
        choices=list(QUANTIZATION.keys()),
        help=HELP["quantization"] + " (required, choices: %(choices)s)",
    )
    parser.add_argument(
        "--model-type",
        type=str,
        default="auto",
        choices=["auto"] + list(MODELS.keys()),
        help=HELP["model_type"] + ' (default: "%(default)s")',
    )
    parser.add_argument(
        "--device",
        default="auto",
        type=detect_device,
        help=HELP["device_quantize"] + ' (default: "%(default)s")',
    )
    parser.add_argument(
        "--source",
        type=str,
        default="auto",
        help=HELP["source"] + ' (default: "%(default)s")',
    )
    parser.add_argument(
        "--source-format",
        type=str,
        choices=["auto", "huggingface-torch", "huggingface-safetensor", "awq"],
        default="auto",
        help=HELP["source_format"] + ' (default: "%(default)s", choices: %(choices)s")',
    )
    parser.add_argument(
        "--output",
        "-o",
        type=_parse_output,
        required=True,
        help=HELP["output_quantize"] + " (required)",
    )
    parser.add_argument(
        "--lora-paths",
        type=str,
        nargs="*",
        action=LoRAPathAction,
        default=None,
        help="The list of LoRA adapters. You can provide a list of either path in str or renamed path in the format (name)=(path)."
    )
    parser.add_argument(
        "--lora-only",
        action="store_true",
        help="Only convert lora weights",
    )

    parsed = parser.parse_args(argv)
    parsed.source, parsed.source_format = detect_weight(
        weight_path=_parse_source(parsed.source, parsed.config),
        config_json_path=parsed.config,
        weight_format=parsed.source_format,
    )
    model = detect_model_type(parsed.model_type, parsed.config)
    convert_weight(
        config=parsed.config,
        quantization=QUANTIZATION[parsed.quantization],
        model=model,
        device=parsed.device,
        source=parsed.source,
        source_format=parsed.source_format,
        lora_paths=parsed.lora_paths,
        lora_only=parsed.lora_only,
        output=parsed.output,
    )
