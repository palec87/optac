import cv2
import matplotlib.pyplot as plt
import numpy as np

img_0 = cv2.imread('data_00.tiff', cv2.IMREAD_UNCHANGED)  # Y16 800x640
img_1 = cv2.imread('data_1.tiff', cv2.IMREAD_UNCHANGED) # Y16 2000x1500
img_2 = cv2.imread('data_2.tiff', cv2.IMREAD_UNCHANGED) # Y800 800x600
img_3 = cv2.imread('data_3.tiff', cv2.IMREAD_UNCHANGED) # Y800 2000x1500
# img_0 = img_0 >> 4
# img_1 = img_1 >> 4

print(img_0.shape, np.amax(img_0), np.amin(img_0))
print(img_1.shape, np.amax(img_1), np.amin(img_1))
print(img_2.shape, np.amax(img_2), np.amin(img_2))
print(img_3.shape, np.amax(img_3), np.amin(img_3))

fig, ax = plt.subplots(2, 2, figsize=(10, 10))
ax[0, 0].hist(img_0.flatten(), bins=range(0, 4100, 20))
ax[0,0].set_title('16bit, 800x640 px')

ax[1, 0].hist(img_1.flatten(), bins=range(0, 4100, 20))
ax[1,0].set_title('16bit, 2000x1500 px')

ax[0, 1].hist(img_2.flatten(), bins=range(256))
ax[0,1].set_title('8bit, 800x640 px')

ax[1, 1].hist(img_3.flatten(), bins=range(256))
ax[1,1].set_title('8bit, 2000x1500 px')

ax[0,0].set_xlim([0,4100])
ax[1,0].set_xlim([0,4100])

ax[0,1].set_xlim([0,256])
ax[1,1].set_xlim([0,256])

ax[0, 0].set_yscale('log')
ax[1, 0].set_yscale('log')
ax[0, 1].set_yscale('log')
ax[1, 1].set_yscale('log')


plt.savefig('compare_dark_counts.png')
plt.show()

