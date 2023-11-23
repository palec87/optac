import numpy as np
from napari.layers import Image, Shapes, Points
from magicgui import magicgui
from napari import Viewer
import napari
import cv2


def normalize_stack(stack, **kwargs):
    '''
    -normalizes n-dimensional stack it to its maximum and minimum values,
    unless normalization values are provided in kwargs,
    -casts the image to 8 bit for fast processing with cv2
    '''
    img = np.float32(stack)
    if 'vmin' in kwargs:
        vmin = kwargs['vmin']
    else:    
        vmin = np.amin(img)
   
    if 'vmax' in kwargs:
        vmax = kwargs['vmax']
    else:    
        vmax = np.amax(img)
    saturation = 1   
    img = saturation * (img-vmin) / (vmax-vmin)
    img = (img*255).astype('uint8') 
    return img, vmin, vmax


def select_rois(first_image, positions, roi_size): 
    rois = []
    half_size = roi_size//2
    for pos in positions:
        y = int(pos[0])
        x = int(pos[1])
        roi = first_image[y-half_size:y+half_size,
                                x-half_size:x+half_size]
        rois.append(roi)
        # zoomed_roi = cv2.resize(roi, [zoom*roi_size,zoom*roi_size])
        # zoomed_rois.append(zoomed_roi)
    return rois


def filter_image(img, sigma):
    if sigma >0:
        sigma = (sigma//2)*2+1 # sigma must be odd in cv2  
        filtered = cv2.medianBlur(img,sigma)
        return filtered
    else:
        return img


def update_position(old_positions, dx_list, dy_list):    
    new_positions = []
    roi_idx = 0
    for pos, dx, dy in zip(old_positions, dx_list, dy_list):
        y1 = pos[0] + dy
        x1 = pos[1] + dx
        new_positions.append([y1,x1])
        roi_idx +=1
        
    return new_positions


def align_with_registration(next_rois, previous_rois, filter_size, roi_size):  
    original_rois = []
    aligned_rois = []
    dx_list = []
    dy_list = []
    
    half_size = roi_size//2
    
    warp_mode = cv2.MOTION_TRANSLATION 
    number_of_iterations = 5000
    termination_eps = 1e-10
    criteria = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT,
                    number_of_iterations,  termination_eps)
    
    warp_matrix = np.eye(2, 3, dtype=np.float32)
    sx, sy = previous_rois[0].shape

    for i in range(len(previous_rois)):
        _, warp_mat = cv2.findTransformECC(previous_rois[i],
                                           next_rois[i],
                                           warpMatrix=warp_matrix,
                                           motionType=warp_mode,
                                           criteria=criteria)
        
        print('warp matrix', i, warp_mat)
        next_roi_aligned = cv2.warpAffine(next_rois[i], warp_matrix, (sx, sy),
                                           flags=cv2.INTER_LINEAR + cv2.WARP_INVERSE_MAP)

        original_roi = previous_rois[i][sy//2 - half_size:sy//2 + half_size,
                                         sx//2 - half_size:sx//2 + half_size]
        
        aligned_roi = next_roi_aligned[sy//2 - half_size:sy//2 + half_size,
                                          sx//2 - half_size:sx//2 + half_size]
        
        original_rois.append(original_roi)
        aligned_rois.append(aligned_roi)

        dx_list.append(warp_mat[0, 2])
        dy_list.append(warp_mat[1, 2])

    return aligned_rois, original_rois, dx_list, dy_list


@magicgui(call_button="Select ROI")
def select_ROIs(viewer: Viewer,
              image: Image,
              points_layer: Points,
              roi_size = 50,
              median_filter_size:int = 3,
              ):
    
    original_stack = np.asarray(image.data)
    normalized, vmin, vmax = normalize_stack(original_stack)
    points = np.asarray(points_layer.data)
    yx_coordinates = points[:,[1,2]]
    positions_list = yx_coordinates.copy()
    filtered_starting_rois = []
    aligned_images = []

    previous_rois = select_rois(normalized[0,:,:],
                                yx_coordinates,
                                roi_size)
    for roi in previous_rois:
        ## 
        filtered_roi = filter_image(roi, median_filter_size)
        filtered_starting_rois.append(filtered_roi)

    # roi_num = len(previous_rois)
    aligned_images.append(filtered_starting_rois)
            
    next_rois = select_rois(normalized[1,:,:],
                            yx_coordinates,
                            roi_size)
    aligned, _, dx, dy = align_with_registration(next_rois,
                                                 previous_rois,
                                                 median_filter_size,
                                                 roi_size)
    aligned_images.append(aligned)
    positions_list = update_position(positions_list, dx, dy)
    aligned_array = np.array(aligned_images)
    # zoomed_array = zoom_stack(aligned_array, roi_size, zoom)
    for roi_idx in range(len(previous_rois)):
        viewer.add_image(aligned_array[:, roi_idx, :, :], name = f'aligned_roi{roi_idx}')



viewer = napari.Viewer()

viewer.window.add_dock_widget(select_ROIs,
                              name = 'register ROIs')
napari.run()