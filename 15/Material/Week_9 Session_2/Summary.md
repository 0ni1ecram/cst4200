Convolutional Network
-----------------------------------------------
Motivation behind: Why fail for images
Core building Blocks: The Convolution, Activation and Pooling Layers
Architecture : Assembling Layers to build powerful networks
Training and regularisation: How CNN learn & Prevent Overfittin
Land Architectures: A tow through History of CNN LeNet, AlexNet, VGG, ResNet
Modern Application: Moving Beyond Classification Towards Detection and Segmentation

Convulational Neural Networks:
-> Mostly applied to analysing imagery class of deep neural networks
-> Trad Neural Networks designed to process with grid like topology.

The Visual Cortex
-> Inspired: CATS, (1959, abel Wesel)
-> Neurons respond to scientific stimuli edges /orientation
-> In restricted area of visual fields
-> Adaptation: Early layers detect, curves and Colors
    while: Deeper layers detect, complex features such as eyes texture and object shapes
-> The Convolution layer: Primary building block for the CNN
                            Defects Local Feature
                            ( Filter/Kernel matrix ) is implemented as weights
                            Over ( input data )

Conv Nets: A class of deep learning neural networks tasked to analyze visual imagery.
Convulation: The element wise Multiplication and sum over sliding window

At each feature computation of dot product 
(input_patch) . (corresponding_filter)

- Output 2D feature map, indicaitng: location feature was spotted (defined by filter)
    Filter:
        Values within are learned during training via backpropagation
        Learn which feature is more important for which task

Hyperparameters Stride & Padding:
    Stride - The step size as the filter moves across inputs
    Padding - Adding a border of zeros around the input volume

The activation layer: After Convulation, it is what is observed to be applied element wise on feature map
    introduces non-linearity to the model
    Rectified Linear Unit (ReLU) most common choice

Pooling Layers
-------------- without heavy source of information effortlessly produces smaller & manageable representations
-> While reducing progressively, the spatial size of representation
- It is a denoising feature, responsible for sharpening features to the next layers.

-> By Downsamplingone reduces number of features (parameters) in the next layer fully connected
-> Model learns more abstract generalized features
-> MAX operation, Computation
                    --------- Calc. avg value from (patch_of_input_data)
                                    summarize the val. to feature_map   { avg_pooling }

ASSEMBLING CLASSIC CNN ARCHITECTURE: Common; stack [Conv -> ReLU -> Pool]
----------------------------------- [Spatial_dimension decrease] directly propotional [layer_depth increase]**-1

iNPUT -> [C Re POOL] -> [C Re POOL] -> [FC Re] -> FC(Softmax) -> OUtPUT
