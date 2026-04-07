#!/usr/bin/env python

import argparse
from pathlib import Path

from unsloth import FastLanguageModel

# https://github.com/ggml-org/llama.cpp/blob/master/examples/quantize/quantize.cpp#L19
ALLOWED_QUANTS = {
    "not_quantized": "Recommended. Fast conversion. Slow inference, big files.",
    "fast_quantized": "Recommended. Fast conversion. OK inference, OK file size.",
    "quantized": "Recommended. Slow conversion. Fast inference, small files.",
    "f32": "Not recommended. Retains 100% accuracy, but super slow and memory hungry.",
    "f16": "Fastest conversion + retains 100% accuracy. Slow and memory hungry.",
    "q8_0": "Fast conversion. High resource use, but generally acceptable.",
    "q4_k_m": "Recommended. Uses Q6_K for half of the attention.wv and feed_forward.w2 tensors, else Q4_K",
    "q5_k_m": "Recommended. Uses Q6_K for half of the attention.wv and feed_forward.w2 tensors, else Q5_K",
    "q2_k": "Uses Q4_K for the attention.vw and feed_forward.w2 tensors, Q2_K for the other tensors.",
    "q3_k_l": "Uses Q5_K for the attention.wv, attention.wo, and feed_forward.w2 tensors, else Q3_K",
    "q3_k_m": "Uses Q4_K for the attention.wv, attention.wo, and feed_forward.w2 tensors, else Q3_K",
    "q3_k_s": "Uses Q3_K for all tensors",
    "q4_0": "Original quant method, 4-bit.",
    "q4_1": "Higher accuracy than q4_0 but not as high as q5_0. However has quicker inference than q5 models.",
    "q4_k_s": "Uses Q4_K for all tensors",
    "q4_k": "alias for q4_k_m",
    "q5_k": "alias for q5_k_m",
    "q5_0": "Higher accuracy, higher resource usage and slower inference.",
    "q5_1": "Even higher accuracy, resource usage and slower inference.",
    "q5_k_s": "Uses Q5_K for all tensors",
    "q6_k": "Uses Q8_K for all tensors",
    "iq2_xxs": "2.06 bpw quantization",
    "iq2_xs": "2.31 bpw quantization",
    "iq3_xxs": "3.06 bpw quantization",
    "q3_k_xs": "3-bit extra small quantization",
}


def quantize_model(
    adapter_path: Path,
    output_path: Path,
    quantization: str,
) -> None:
    if quantization not in ALLOWED_QUANTS.keys():
        raise ValueError("Please choose a proper quant. setting.")

    model, tokenizer = FastLanguageModel.from_pretrained(
        adapter_path.as_posix()
    )
    model.save_pretained_gguf(
        output_path.as_posix(),
        tokenizer,
        quantization,
    )


def main(args: argparse.Namespace) -> None:
    quantize_model(args.adapter_path, args.output_path, args.quantization)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Quantize a model adapter.")
    parser.add_argument(
        "adapter_path",
        type=Path,
        help="Path to the model adapter to quantize.",
    )
    parser.add_argument(
        "output_path",
        type=Path,
        help="Path to save the quantized model adapter to.",
    )
    parser.add_argument(
        "quantization",
        type=str,
        default="q8_0",
        help=f"Quantization method to use. Allowed values: {', '.join(ALLOWED_QUANTS.keys())}",
    )
    args = parser.parse_args()
    main(args)
