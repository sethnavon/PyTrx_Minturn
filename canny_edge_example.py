import numpy as np
import matplotlib.pyplot as plt
from scipy import ndimage as ndi
from skimage import feature
from skimage.io import imread


# Define image filepaths
inglecam_img1 = 'cam_data/images/2019/INGLEFIELD_CAM_StarDot1_20190712_030000.jpg'
inglecam_img2 = 'cam_data/images/2019/INGLEFIELD_CAM_StarDot1_20190810_210000.jpg'
inglecam_img3 = 'cam_data/images/2019/INGLEFIELD_CAM_StarDot1_20190904_000000.jpg'

# create figure
fig1, ax1 = plt.subplots(nrows=3, ncols=3, figsize=(12, 8), sharex= 'col', sharey='row')

# adjust spacing between subplots
fig1.subplots_adjust(hspace=0)

a=0
for i in [inglecam_img1, inglecam_img2, inglecam_img3]:
    
    # Retrieve image
    im = imread(i, as_gray= True)
    im = ndi.gaussian_filter(im, 3)
    
    # Compute the Canny filter for two values of sigma
    edge1 = feature.canny(im)
    edge2 = feature.canny(im, sigma=3)
    
    # Compute row with most edges
    rows1, cols1 = edge2.shape
    rowsum = np.sum(edge2.astype(int), axis = 1)
    edges2line = [rowsum.argmax()]*cols1
    
    # Plot
    ax1[a,0].imshow(im, cmap='gray')
    ax1[a,1].plot(rowsum, np.arange(rows1), color = "black", linewidth=0.5)
    ax1[a,2].plot(edges2line, color = "red", linewidth=1)
    ax1[a,2].imshow(edge1, cmap='gray', vmin=0, vmax=0.25)  # set vmin and vmax to adjust the contrast
    
    # Set label
    name = i.split('_')[-2]
    date = name[0:4] + '/' + name[4:6] + '/' + name[-2:]
    ax1[a,0].set_ylabel('Row (px)', fontsize=10)

    # Add labels to leftmost y-axis and bottom x-axis
    if a == 2:
        ax1[a,0].set_xlabel('Column (px)', fontsize=10)
        ax1[a,1].set_xlabel('Canny edge (px)', fontsize=10)
        ax1[a,2].set_xlabel('Column (px)', fontsize=10)
        
    # Add date to the right y-axis
    ax1[a,2].yaxis.set_label_position("right")
    ax1[a,2].set_ylabel(date, fontsize=10)
        
    a+=1
    
    for row in range(3):
        ax1[row,0].invert_yaxis()
        ax1[row,1].invert_yaxis()
        ax1[row,2].invert_yaxis()
        
    if a == 1 or a == 3:
        ax1[a-1,0].invert_yaxis()
        ax1[a-1,1].invert_yaxis()
        ax1[a-1,2].invert_yaxis()

    ## Make sure all axes have same size/shape
    for row in range(3):
        for col in range(3):
            ax1[row,col].set_box_aspect(im.shape[0]/im.shape[1])
        # plt.tight_layout()

# Save and show plot
fig1.savefig('figures/figure4.png', dpi=600)
plt.show()

print('Finished')
