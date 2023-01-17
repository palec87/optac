from scipy.fftpack import fft, ifft
from scipy.interpolate import interp1d
import numpy as np
import matplotlib.pyplot as plt


class Radon():
    def __init__(self, line, steps: int) -> None:
        self.line = line
        self.n_steps = steps
        self.sinogram = np.zeros((len(line), steps))
        self.output_size = len(line)
        self.output = np.zeros((len(line), len(line)))
        self.radon_img = self._sinogram_circle_to_square(self.sinogram)
        self.radon_img_shape = self.radon_img.shape[0]
        self.offset = (self.radon_img_shape-self.output_size)//2
        self.projection_size_padded = max(
                                        64,
                                        int(2 ** np.ceil(np.log2(2 * self.radon_img_shape))))
        self.radius = self.output_size // 2
        self.xpr, self.ypr = np.mgrid[:self.output_size, :self.output_size] - self.radius
        self.x = np.arange(self.radon_img_shape) - self.radon_img_shape // 2
        self.theta = np.deg2rad(
                        np.linspace(0., 360., self.n_steps, endpoint=False)
                        )
        self.update_recon(self.line, 0)

    def update_recon(self, line_in, step):
        self.line = line_in
        # padding line
        line = np.zeros(self.projection_size_padded)
        line[self.offset:len(line_in)+self.offset] = line_in

        # fft filtering of the line
        fourier_filter = self._get_fourier_filter(self.projection_size_padded)
        projection = fft(line) * fourier_filter
        radon_filtered = np.real(ifft(projection)[:self.radon_img_shape])

        # interpolation on the circle
        interpolation = 'linear'
        t = self.ypr * np.cos(self.theta[step]) - self.xpr * np.sin(self.theta[step])
        if interpolation == 'linear':
            interpolant = interp1d(self.x, radon_filtered, kind='linear',
                                   bounds_error=False, fill_value=0)
        elif interpolation == 'cubic':
            interpolant = interp1d(self.x, radon_filtered, kind='cubic',
                                   bounds_error=False, fill_value=0)
        else:
            raise ValueError
        self.output += interpolant(t)

    def _get_fourier_filter(self, size):
        '''size needs to be even
        Only ramp filter implemented
        '''
        n = np.concatenate((np.arange(1, size / 2 + 1, 2, dtype=int),
                            np.arange(size / 2 - 1, 0, -2, dtype=int)))
        f = np.zeros(size)
        f[0] = 0.25
        f[1::2] = -1 / (np.pi * n) ** 2

        # Computing the ramp filter from the fourier transform of its
        # frequency domain representation lessens artifacts and removes a
        # small bias as explained in [1], Chap 3. Equation 61
        fourier_filter = 2 * np.real(fft(f))         # ramp filter
        return fourier_filter

    def _sinogram_circle_to_square(self, sinogram):
        diagonal = int(np.ceil(np.sqrt(2) * sinogram.shape[0]))
        pad = diagonal - sinogram.shape[0]
        old_center = sinogram.shape[0] // 2
        new_center = diagonal // 2
        pad_before = new_center - old_center
        pad_width = ((pad_before, pad - pad_before), (0, 0))
        return np.pad(sinogram, pad_width, mode='constant', constant_values=0)


def main():
    sinogram = np.loadtxt('data\\sinogram.txt')
    radon = Radon(sinogram[:, 0], sinogram.shape[1])
    for i in range(1, sinogram.shape[1]):
        radon.update_recon(sinogram[:, i], i)
        if not i % 10:
            plt.imshow(radon.output)
            plt.colorbar()
            plt.title(f'{i}/{sinogram.shape[1]} angles finished.')
            plt.show()
    plt.imshow(radon.output)
    plt.colorbar()
    plt.title('final reconstruction')
    plt.savefig('tests\\radon_test.jpg')
    plt.show()


if __name__ == '__main__':
    main()
