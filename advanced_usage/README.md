# Advanced Usage

The purpose of this Advanced Usage Guide is to provide additional tooling, tips, and guidance for building image similarity models. 

## Tips and "Gotchas"

-  **Training Data**: To build an image similarity model that will recognize and suggest plants, you would need to make sure your model was trained using images of similar plants. As a counter example, if you passed the model an image of a lobster and it had never seen anything similar, it might suggest photos of things that are not close to lobsters, but were more similar than any images it had already seen. We've provided a general model that was trained on 101 different categories, but for a more specific use case, it may make sense to change your training data set. Alternatively for a more general use case, Caltech also provides a data set using [256 categories](http://www.vision.caltech.edu/Image_Datasets/Caltech256/). 
-  **Model Runtime**:  The out-of-the box model takes a long time to train on CPU. Try limiting the amount of data used to train the model if you need to build it more quickly. Likely, you don't need all 9,145 images of from 101 different categories to get something working. You might want to try using 2 categories to begin with. Also, set `max_iterations` lower (default value is 10) in the `turicreate.image_similarity.create` function if you want something to train quickly (at the cost of reduced accuracy).
-  **Model Size**: In addition to the tips above, try using the `squeezenet_v1.1` model in the `turicreate.image_similarity.create` function which will reduce the size of the model significantly. This may also impact the filtering or proposal abilities of the model to some degree.

## Resources

-  `images_in_turicreate.ipynb`: Gives some tips on wrangling image data in Turi Create, detailing proper formatting and several helper functions.

## Need Help?
Please contact us with questions or feedback! Here are two ways:


-  [**Signup for our Slack Channel**](https://join.slack.com/t/metismachine-skafos/shared_invite/enQtNTAxMzEwOTk2NzA5LThjMmMyY2JkNTkwNDQ1YjgyYjFiY2MyMjRkMzYyM2E4MjUxNTJmYmQyODVhZWM2MjQwMjE5ZGM1Y2YwN2M5ODI)
-  [**Find us on Reddit**](https://reddit.com/r/skafos) 

Also check out Turi Create's [**documentation**](https://apple.github.io/turicreate/docs/userguide/image_similarity/) on image similarity basics.
