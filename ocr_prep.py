import cv2
from matplotlib import pyplot as plt
image_file="data/receipts/bill1.jpg"
img=cv2.imread(image_file)

'''cv2.imshow("original image", img)
cv2.waitKey(5)'''

def display(img_path):
    dpi=80
    im_data=plt.imread(img_path)
    height,width, depth= im_data.shape
    
    figsize=width/float(dpi), height/float(dpi)
    fig=plt.figure(figsize=figsize)
    ax=fig.add_axes([0,0,1,1])

    ax.axis('off')
    ax.imshow(im_data,cmap='gray')

    plt.show()

display(image_file)