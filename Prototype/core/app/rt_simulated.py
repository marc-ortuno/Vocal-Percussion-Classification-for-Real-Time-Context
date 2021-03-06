import numpy as np
from interfaces import pre_processing, activity_detection, feature_extraction, classificator
import pandas as pd
# noinspection INSPECTION_NAME

def init_pre_processing(by_pass=False, bands = 8):
    global pre_processing_by_pass
    global n_bands

    n_bands = bands
    pre_processing_by_pass = by_pass


def init_activity_detection(func_type=1, by_pass=False):
    # Activity detection variables
    global onset_location
    global last_onset
    global hfc
    global activity_detection_type  # Function name
    global activiy_detection_by_pass
    global previous_hfc
    global previous_th

    onset_location = []
    last_onset = False
    hfc = 0
    previous_hfc = np.zeros(n_bands)
    previous_th = np.zeros(n_bands)
    activity_detection_type = func_type
    activiy_detection_by_pass = by_pass


def init_feature_extraction(func_type="mfcc", n_mfcc_arg=20, by_pass=False, norm_file=[]):
    # Feature extraction variables
    global active_signal
    global features
    global n_mfcc
    global feature_extraction_by_pass
    global normalization_values
    global feature_extraction_type  # Function name

    normalization_values = norm_file
    active_signal = []
    features = []
    n_mfcc = n_mfcc_arg
    feature_extraction_type = func_type
    feature_extraction_by_pass = by_pass


def init_classificator(knn_model=[], by_pass=False):
    # Classificator Variables
    global model
    global predicted
    global classificator_by_pass

    model = knn_model
    predicted = []
    classificator_by_pass = by_pass


# Init audio process variables
def init(sr, b_len, audio_len=0):
    # declare variables used in `process`
    # Audio details
    global samp_freq
    global buffer_len
    global onset_timeout
    global onset_duration
    global audio_size
    global execution_time
    global highest_peak

    samp_freq = sr
    buffer_len = b_len
    avg_duration = 0.100 # in seconds
    onset_duration = int(avg_duration / (b_len / sr))  # 150ms average duration of a class
    onset_timeout = onset_duration

    audio_size = audio_len
    execution_time = 0
    highest_peak = np.full(n_bands, b_len*0.8)



# the process function!
def process(input_buffer, output_buffer):
    global last_onset
    global active_signal
    global onset_timeout
    global highest_peak
    global execution_time
    global previous_hfc
    global previous_th

    features = []
    activity_detected = False
    class_type = ""

    if not pre_processing_by_pass:

        # Pre-Processing Block
        subband_signal, n_signal = pre_processing(input_buffer, samp_freq, n_bands)

        if not activiy_detection_by_pass:

            # activity_detection_evaluation Block
            onset, hfc, threshold, highest_peak = activity_detection(activity_detection_type, subband_signal, samp_freq,
                                                                     buffer_len, previous_hfc, highest_peak)
            previous_hfc = np.vstack((previous_hfc, hfc))
            previous_th = np.vstack((previous_th, threshold))

            # To prevent repeated reporting of an
            # onset (and thus producing numerous false positive detections), an
            # onset is only reported if no onsets have been detected in the previous three frames (30 ms aprox).
            mHfc = previous_hfc[-2:].sum(axis=1)
            mTh = previous_th[-2:].sum(axis=1)
            if last_onset is True and onset is False:
                if onset_timeout > 0:
                    onset = True
                    onset_timeout -= 1
                    activity_detected = False
                else:
                    onset = False
                    onset_timeout = onset_duration
                    activity_detected = True

                if len(mHfc) > 1 and int(mHfc[1]) < int(mHfc[0]) and len(mTh) > 1 and int(mTh[1]) <= int(mTh[0]) and\
                        int(mHfc[0]) - int(mHfc[1]) < (4 * buffer_len):
                    onset = False
                    onset_timeout = onset_duration
                    activity_detected = True

            if onset:
                active_signal.extend(
                    input_buffer)  # Until we get an offset, the active sound is stored for later do feature extraction an onset is False: classification.
                onset_location.extend(np.ones(buffer_len))  # Onset location for visual analysis
            else:
                onset_location.extend(np.zeros(buffer_len))

            # Offset detected
            if activity_detected: # or (int(execution_time*samp_freq) + buffer_len >= audio_size):

                if not feature_extraction_by_pass:

                    # Feature Extraction Block
                    features = feature_extraction(feature_extraction_type, active_signal, samp_freq, n_mfcc, buffer_len,
                                                  normalization_values)
                    active_signal = []  # Clean active signal buffer

                    if not classificator_by_pass:
                        # Classificator Block
                        class_type = classificator(features, model)
                        predicted.append(class_type)

            last_onset = onset

        # Update execution time
        execution_time += (buffer_len / samp_freq)

    return n_signal, features, hfc, predicted, onset_location, threshold, class_type


def main(audio, buffer_len=512):
    # Signal details
    signal = audio.waveform
    samp_freq = audio.sample_rate
    n_buffers = len(signal) // buffer_len

    # Init process variables
    init(samp_freq, buffer_len, n_buffers * buffer_len)

    data_type = signal.dtype
    # allocate input and output buffers
    input_buffer = np.zeros(buffer_len, dtype=data_type)
    output_buffer = np.zeros(buffer_len, dtype=data_type)

    onset_location = []
    total_features = []
    total_hfc = []
    total_th = []
    # simulate block based processing
    signal_proc = np.zeros(n_buffers * buffer_len, dtype=data_type)

    for k in range(n_buffers):

        # index the appropriate samples
        input_buffer = signal[k * buffer_len:(k + 1) * buffer_len]
        output_buffer, features, hfc, predicted, onset_location, threshold, _ = process(input_buffer, output_buffer)

        signal_proc[k * buffer_len:(k + 1) * buffer_len] = output_buffer

        total_features.extend(features)

        if type(hfc) is np.ndarray:
            total_hfc.extend([np.sum(hfc)] * output_buffer.size)
        else:
            total_hfc.extend([np.sum(hfc)] * output_buffer.size)

        if type(threshold) is np.ndarray:
            total_th.extend([np.sum(threshold)] * output_buffer.size)
        else:
            total_th.extend([np.sum(threshold)] * output_buffer.size)

    # return in a dictionary
    return {'SIGNAL_PROCESSED': signal_proc, 'ONSET_LOCATIONS': onset_location, 'HFC': total_hfc, 'THRESHOLD': total_th,
            'PREDICTION': predicted, 'FEATURES': total_features}
