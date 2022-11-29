import cv2
import matplotlib.pyplot as plt

for i in range(5):
    capture = cv2.VideoCapture(i)
    ret, frame = capture.read()

    if ret:
        print(frame.shape)
        plt.imshow(frame)
        plt.title(f'input device number {i}.')
        plt.show()
    else:
        print(f'no input ret is {ret}.')

    capture.release()
