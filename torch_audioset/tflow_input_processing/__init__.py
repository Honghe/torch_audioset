import torch
from .vggish_utils import mel_features
from .yamnet_utils import features as features_lib
from ..params import VGGishParams, YAMNetParams


class WaveformToInput():
    def __init__(self, method='vggish'):
        assert method in ('vggish', 'yamnet')
        self.method = method

    def __call__(self, waveform, sample_rate):
        if isinstance(waveform, torch.Tensor):
            waveform = waveform.T.numpy()
        func = vggish_transform if self.method == 'vggish' else yamnet_transform
        return func(waveform, sample_rate)


def vggish_transform(waveform, sample_rate):
    '''
    Args:
        waveform: torch tsr [1, num_channels, num_steps]
        sample_rate: per second sample rate
    '''
    import resampy
    data = waveform.squeeze(axis=0)
    # Resample to the rate assumed by VGGish.
    if sample_rate != VGGishParams.SAMPLE_RATE:
        data = resampy.resample(data, sample_rate, VGGishParams.SAMPLE_RATE)

    # Compute log mel spectrogram features.
    log_mel = mel_features.log_mel_spectrogram(
        data,
        audio_sample_rate=VGGishParams.SAMPLE_RATE,
        log_offset=VGGishParams.LOG_OFFSET,
        window_length_secs=VGGishParams.STFT_WINDOW_LENGTH_SECONDS,
        hop_length_secs=VGGishParams.STFT_HOP_LENGTH_SECONDS,
        num_mel_bins=VGGishParams.NUM_MEL_BINS,
        lower_edge_hertz=VGGishParams.MEL_MIN_HZ,
        upper_edge_hertz=VGGishParams.MEL_MAX_HZ
    )

    # Frame features into examples.
    features_sample_rate = 1.0 / VGGishParams.STFT_HOP_LENGTH_SECONDS
    example_window_length = int(round(
        VGGishParams.EXAMPLE_WINDOW_SECONDS * features_sample_rate
    ))
    example_hop_length = int(round(
        VGGishParams.EXAMPLE_HOP_SECONDS * features_sample_rate
    ))
    log_mel_examples = mel_features.frame(
        log_mel, window_length=example_window_length, hop_length=example_hop_length
    )
    return log_mel_examples


def yamnet_transform(waveform, sample_rate):
    '''
    Args:
        waveform: torch tsr [1, num_channels, num_steps]
        sample_rate: per second sample rate
    '''
    # FIXME need to make this run somehow in "eager" mode
    import tensorflow as tf
    spectrogram = features_lib.waveform_to_log_mel_spectrogram(
        tf.squeeze(waveform, axis=0), YAMNetParams
    )
    patches = features_lib.spectrogram_to_patches(
        spectrogram, YAMNetParams
    )
    return patches
