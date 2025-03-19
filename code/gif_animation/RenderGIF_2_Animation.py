# Imports
import PIL.Image
from typing import List

# ##############################################################################
# # # Methods # # GREECE B_TRACK ANIMATION
# ##############################################################################


def render_gif_animation(lst_image_files: List[str], target_file: str, speed:int=100, first_last_slow:bool=True, add=0, crop_default=True, crop=[]):
    """
    This function reads static images from a list of image files, and stores 
    all of them in an GIF animation.
    
    Parameters
    ----------
    lst_image_files: List[str]
        A list with image files that shall be connected to a GIF animation.
    target_file : str
        The target file to store the GIF into.
    speed : int
        Optional, Defualt: 100. The time per image. The slower the faster the animation.
    first_last_slow : bool
        Optional, Default : True. This will repeat the first and the last 
        image for ten times, so the animation does not directly run.
        
    Returns
    -------
    None
    """
    frames = []
    if first_last_slow:
        for x in range(0,10):
            image = PIL.Image.open(lst_image_files[0])
            if crop_default:
                image = image.crop((int(image.size[0]/2-image.size[1]/2), 0, int(image.size[0]/2+image.size[1]/2), image.size[1]))
            else:
                image = image.crop((crop[0], crop[1], crop[2], crop[3]))
            frames.append(image)
    for file in lst_image_files:
        image = PIL.Image.open(file)
        if crop_default:
            image = image.crop((int(image.size[0]/2-image.size[1]/2), 0, int(image.size[0]/2+image.size[1]/2), image.size[1]))
        else:
            image = image.crop((crop[0], crop[1], crop[2], crop[3]))
        frames.append(image)
        print(file)
    if first_last_slow:
        for x in range(0,10):
            frames.append(frames[-1])
    frames[0].save(target_file, format='GIF',
                    append_images=frames[1:],
                    save_all=True,
                    duration=speed, loop=0)
    
import os
path = "figures_car_grp"
files = os.listdir(path)
files = [path+"/"+f for f in files]
# files = files[0:1000]

render_gif_animation(files, path+".gif", speed=100, first_last_slow=True, add=0) #add=52
# render_gif_animation(files, path+".gif", speed=100, first_last_slow=True, add=0, crop_default=False, crop=[0, 350, 1910, 700]) #add=52