#!/usr/bin/env python

from optac.modules.phantoms_argonne import shepp3d
import matplotlib.pyplot as plt
import numpy as np

plt.ion()

data = 255*shepp3d(128, dtype='float32')
print('maximum intensity of the pixel', np.amax(data))
data = data.astype('int16')

# fig, ax = plt.subplots(1, 5, sharey=True)
# ax[0].imshow(data[:, :, 20])
# ax[1].imshow(data[:, :, 40])
# ax[2].imshow(data[:, :, 60])
# ax[3].imshow(data[:, :, 80])
# ax[4].imshow(data[:, :, 100])
# plt.show()
# plt.pause(1)
# plt.clf()

# one vertical slice of the object
frame = data[:, :, 64]
plt.imshow(frame)
plt.colorbar()
plt.show()
plt.pause(1)
plt.clf()

#  Histogram of one slice
hist, edges = np.histogram(frame.flatten(), bins=20)
plt.hist(edges[:-1], edges, weights=hist)
plt.title('Histogram of one slice')
plt.show()
plt.pause(1)
plt.clf()

plt.ioff()

# Display of the mean intensity projection
mean_proj = np.mean(data, axis=2)
plt.imshow(mean_proj, cmap=plt.cm.Greys_r)
plt.colorbar()
plt.show()
