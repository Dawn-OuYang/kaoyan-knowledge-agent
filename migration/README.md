# Ascend migration artifacts

This directory records the files used for the final Ascend migration and
validation run.

| File | Purpose |
| --- | --- |
| `qwen35-0p8b-rag-sft-v2.yaml` | MindSpeed-MM fine-tuning configuration used for the iter80 model |
| `mindspeed-mm-trainer-final.patch` | Validation dataloader compatibility patch applied to MindSpeed-MM |
| `trainer.py.final` | Patched `mindspeed_mm/fsdp/train/trainer.py` retained for reproduction |
| `FREEZE_METADATA.txt` | Frozen model and upstream repository revision metadata |
| `SHA256SUMS.txt` | SHA-256 checksums for the migration artifacts in this directory |

The fine-tuned model weights are not stored in GitHub. They are provided
separately in the competition submission package. Paths beginning with
`/workspace/kaoyan-lab` refer to the Ascend WebIDE validation environment.
