import numpy as np

from dataset import get_dataset, dataset_analyzer
from interfaces import pre_processing, activity_detection, feature_extraction, classificator, train_model
from utils import plot_audio, plot_spectrum, plot_odf,plot_librosa_spectrum,plot_fft,plot_confusion_matrix,plot_evaluation_report
from test import evaluate_system
from sklearn.metrics import classification_report
import pickle 

'''
Real-Time simulation
init(): init of global variables
procces(): procces each block/buffer
main(): main
'''

# parameters
filename = 'finalized_model.sav' #model name
knn_model = pickle.load(open(filename, 'rb'))

# state variables
def init():

    # declare variables used in `process`
    # global
    global groundtruth
    global predicted 
    global n_fft
    global hop_size
    global features
    global last_onset 
    global hfc
    global n_mfcc
    global active_signal
    global onset_location

    groundtruth = ['Kick', 'HH', 'Snare', 'HH','Kick', 'HH', 'Snare', 'HH','Kick', 'HH', 'Snare', 'HH','Kick', 'Kick', 'HH', 'Snare' ]
    predicted = []

    onset_location = []

    n_fft = 256
    hop_size = 64
    features = []
    last_onset = False
    hfc = []

    active_signal = []
    n_mfcc = 40

    return


# the process function!
def process(input_buffer, output_buffer, buffer_len,samp_freq):

    global last_onset
    global hfc
    global features
    global n_fft
    global hop_size
    global n_mfcc
    global active_signal
    global onset_location

    n_signal = pre_processing(input_buffer,samp_freq)

    #Detect onset
    onset = activity_detection(n_signal,samp_freq,n_fft,hop_size)

    # Only calculated when the onset is detected
    if onset:
        active_signal.extend(input_buffer) # Until we get an offset, the active sound is stored for later do feature extraction and classification.
        onset_location.extend(np.ones(buffer_len)) # Onset location for visual analysis
    else:
        onset_location.extend(np.zeros(buffer_len))

    #Offset detected
    if last_onset is True and onset is False:
        features = feature_extraction(active_signal,samp_freq,n_mfcc)
        predicted.append(classificator(features,knn_model))
        features = []
        active_signal = [] #Clean active signal buffer
    
    last_onset = onset

    output_buffer = n_signal
    return output_buffer


def main(audio):

    buffer_len = 512

    signal = audio.waveform
    samp_freq = audio.sample_rate
    #duration = audio.duration

    n_buffers = len(signal)//buffer_len
    data_type = signal.dtype
    
    # allocate input and output buffers
    input_buffer = np.zeros(buffer_len, dtype=data_type)
    output_buffer = np.zeros(buffer_len, dtype=data_type)

    #init system variables
    init()

    # simulate block based processing
    signal_proc = np.zeros(n_buffers*buffer_len, dtype=data_type)

    for k in range(n_buffers):

        # index the appropriate samples
        input_buffer = signal[k*buffer_len:(k+1)*buffer_len]
        output_buffer = process(input_buffer, output_buffer, buffer_len,samp_freq)
        signal_proc[k*buffer_len:(k+1)*buffer_len] = output_buffer

    plot_audio(signal,signal_proc,samp_freq)
    plot_odf(signal_proc,samp_freq,onset_location)
    report, cm = evaluate_system(groundtruth,predicted)

    #EVALUATION METRICS PLOTS
    plot_evaluation_report(report)
    plot_confusion_matrix(cm)