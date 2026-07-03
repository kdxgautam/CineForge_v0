# LR-ASD Local Setup Notes

`external/LR-ASD/` is intentionally ignored by Git. Keep that checkout and its
model weights local, then recreate it after cloning this repo.

Clone source:

```bash
mkdir -p external
git clone https://github.com/Junhua-Liao/LR-ASD.git external/LR-ASD
```

The backend expects:

- `external/LR-ASD/Columbia_test.py`
- `external/LR-ASD/ASD.py`
- `external/LR-ASD/weight/pretrain_AVA.model`
- `external/LR-ASD/weight/finetuning_TalkSet.model` if you use TalkSet
- `external/LR-ASD/model/faceDetector/s3fd/sfd_face.pth`

If `sfd_face.pth` is missing after cloning LR-ASD, download it from the file ID
used by the upstream face detector:

```bash
cd external/LR-ASD
../../.venv/bin/uv run gdown --id 1KafnHz7ccT-3IyddBsL5yi2xGtxAKypt -O model/faceDetector/s3fd/sfd_face.pth
cd ../..
```

## Patches Used Locally

Apply these changes inside the LR-ASD checkout if the upstream copy is not
already compatible with this environment.

1. In `Columbia_test.py`, make OpenCV/scenedetect compatible:

```python
_original_cv2_split = cv2.split
cv2.split = lambda *args, **kwargs: list(_original_cv2_split(*args, **kwargs))
```

2. In `Columbia_test.py`, choose device dynamically:

```python
args.device = "cuda" if torch.cuda.is_available() else "cpu"
```

Then replace hardcoded CUDA calls:

```python
S3FD(device="cuda")
s = ASD()
tensor.cuda()
```

with device-aware versions:

```python
S3FD(device=args.device)
s = ASD(device=args.device)
tensor.to(args.device)
```

3. In `ASD.py`, accept and use a device:

```python
def __init__(self, device=None):
    self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
```

Move the model, loss, and tensors with `.to(self.device)`, and load weights with:

```python
torch.load(path, map_location=self.device)
```

4. In `model/faceDetector/s3fd/box_utils.py`, replace the removed NumPy alias:

```python
return np.array(keep).astype(np.int)
```

with:

```python
return np.array(keep).astype(int)
```

Without this patch, LR-ASD can fail during face detection with:

```text
AttributeError: module 'numpy' has no attribute 'int'
```

These patches let LR-ASD run on either CUDA or CPU from the main backend process
and keep the upstream face detector compatible with modern NumPy.
