class Frame():
    '''
    class for processing chunks of frames comming from the camera
    Mostly averaging and software binning.
    '''
    def __init__(self, frame, count, mx):
        self.frame = frame
        self.no_data_count = count
        self.minmax = mx

    def update_frame(self, frame, count, mx):
        self.frame = frame
        self.no_data_count = count
        self.minmax = mx
