import torch

from .runtime import configure_cuda_runtime


def load_whisperx():
    """Import WhisperX after applying compatibility patches for this stack."""

    configure_cuda_runtime()

    import torchaudio

    if not hasattr(torchaudio, "AudioMetaData"):
        class AudioMetaData:
            def __init__(
                self,
                sample_rate=None,
                num_frames=None,
                num_channels=None,
                bits_per_sample=None,
                encoding=None,
            ):
                self.sample_rate = sample_rate
                self.num_frames = num_frames
                self.num_channels = num_channels
                self.bits_per_sample = bits_per_sample
                self.encoding = encoding

        torchaudio.AudioMetaData = AudioMetaData

    if not hasattr(torchaudio, "list_audio_backends"):
        torchaudio.list_audio_backends = lambda: ["soundfile"]

    if not hasattr(torchaudio, "info"):
        torchaudio.info = lambda *_args, **_kwargs: torchaudio.AudioMetaData()

    if not getattr(torch.load, "_cineforge_weights_patch", False):
        original_torch_load = torch.load

        def patched_torch_load(*args, **kwargs):
            kwargs["weights_only"] = False
            return original_torch_load(*args, **kwargs)

        patched_torch_load._cineforge_weights_patch = True
        torch.load = patched_torch_load

    import whisperx

    return whisperx
