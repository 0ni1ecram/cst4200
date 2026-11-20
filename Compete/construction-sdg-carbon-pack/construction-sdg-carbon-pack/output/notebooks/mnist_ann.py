"""MNIST ANN — Sequential model with He-Normal init, L2, BatchNorm, Dropout.

Mirrors the 4-stage task in the whiteboard image.
Run:  python3 mnist_ann.py            (CPU; ~30-60 s)
"""
import warnings, os
warnings.filterwarnings("ignore")
os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")

import numpy as np
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras.layers import (
    Dense, BatchNormalization, Dropout, Flatten, Input)
from tensorflow.keras.initializers import HeNormal
from tensorflow.keras.regularizers import L2
from sklearn.metrics import classification_report, confusion_matrix

SEED = 42
keras.utils.set_random_seed(SEED)
L2_SCALE = 1e-4           # tune: 1e-5 (light) .. 1e-3 (heavy)
DROPOUT_RATE = 0.25

# ============================================================
# STAGE 1 — Load MNIST dataset + prepare it
# ============================================================
# 60 000 train / 10 000 test images, each 28x28 grayscale (0..255), labels 0..9.
(x_train, y_train), (x_test, y_test) = keras.datasets.mnist.load_data()

# Normalise to 0..1. BatchNorm fixes per-layer stats anyway, but scaling the
# raw inputs keeps the first layer's gradients well-conditioned.
x_train = x_train.astype("float32") / 255.0
x_test  = x_test.astype("float32")  / 255.0

# Flatten the 28x28 grid into a 784-vector for a *dense* (ANN, not CNN) net.
NUM_CLASSES = 10
y_train_oh = keras.utils.to_categorical(y_train, NUM_CLASSES)
y_test_oh  = keras.utils.to_categorical(y_test,  NUM_CLASSES)

print("Stage 1 | x_train", x_train.shape, "x_test", x_test.shape,
      "| pixel range", x_train.min(), x_train.max())

# ============================================================
# STAGE 2 + 3 — Prepare the Sequential model
#   Architecture requirements from the image:
#     - Weight initialisation: He Normal (best match for ReLU)
#     - L2 regularisation      : penalises large weights -> fights overfitting
#     - Batch Normalisation    : standardises each layer's activations
#     - Dropout regularisation : randomly zeroes units during training
# ============================================================
def build_model(l2_scale=L2_SCALE, dropout=DROPOUT_RATE):
    """Dense ANN: [HeNormal + L2] -> Dense/ReLU -> BatchNorm -> Dropout (x3)."""
    # `he_normal` initialiser is the right choice because every hidden layer
    # uses ReLU: it scales variance by sqrt(2/fan_in) to account for the
    # half of activations ReLU clips to zero. `kernel_regularizer` adds the
    # L2 weight penalty to the loss.
    H = dict(units=512, activation="relu",
             kernel_initializer=HeNormal(seed=SEED),
             kernel_regularizer=L2(l2_scale))
    return keras.Sequential([
        Input(shape=(28, 28, 1)),
        Flatten(name="flatten_in"),

        Dense(**H, name="dense_1"),            # He normal + L2
        BatchNormalization(name="bn_1"),        # BN: zero-mean/unit-var per batch
        Dropout(dropout, name="drop_1"),        # dropout: train-time noise

        Dense(**H, name="dense_2"),
        BatchNormalization(name="bn_2"),
        Dropout(dropout, name="drop_2"),

        Dense(256, activation="relu",
              kernel_initializer=HeNormal(seed=SEED),
              kernel_regularizer=L2(l2_scale), name="dense_3"),
        BatchNormalization(name="bn_3"),
        Dropout(dropout, name="drop_3"),

        Dense(NUM_CLASSES, activation="softmax",
              kernel_initializer=HeNormal(seed=SEED),
              kernel_regularizer=L2(l2_scale), name="output"),
    ])

model = build_model()
model.compile(
    optimizer="adam",                                # adaptive LR, pairs well with BN
    loss="categorical_crossentropy",                 # multi-class target
    metrics=["accuracy"],
)
model.summary()

# ============================================================
# STAGE 4 — Fit the model + evaluate on training AND testing
# ============================================================
# Pull 10 000 samples out of the 60 000 train set to form a validation split.
# Validation is used by EarlyStopping to pick the best epoch; it is NOT the
# same as the held-out test set, which is only touched once at the end.
x_val, y_val = x_train[-10000:], y_train_oh[-10000:]
x_fit, y_fit = x_train[:-10000], y_train_oh[:-10000]

callbacks = [
    keras.callbacks.EarlyStopping(
        monitor="val_loss", patience=3, restore_best_weights=True),
]

history = model.fit(
    x_fit, y_fit,
    batch_size=128,          # BatchNorm stats are computed per batch -> keep it
                             # small enough to be noisy-but-stable (~128..256)
    epochs=20,
    validation_data=(x_val, y_val),
    callbacks=callbacks,
    verbose=2,
)

# --- Evaluate on BOTH training and testing sets (the task's explicit ask) ---
def l2_penalty():
    """Sum of the L2 weight penalties added by every Dense layer."""
    return float(tf.add_n(model.losses)) if model.losses else 0.0

def evaluate(name, x, y_oh, y_hard):
    tl, ta = model.evaluate(x, y_oh, verbose=0)   # tl already includes L2 term
    preds  = np.argmax(model.predict(x, verbose=0), axis=1)
    print(f"\n== {name} ==  loss {tl:.4f}  acc {ta*100:.2f}%  "
          f"(of which L2 penalty {l2_penalty():.4f})")
    print(classification_report(y_hard, preds, digits=4))
    return ta, preds

# Normalise the training set for inference too.
tr_acc, tr_pred = evaluate("TRAIN (fit split)", x_fit, y_fit, y_train[:-10000])
te_acc, te_pred = evaluate("TEST", x_test, y_test_oh, y_test)

# Confusion matrix on the test set -> where does it still slip?
cm = confusion_matrix(y_test, te_pred)
print("Test confusion matrix:\n", cm)
print(f"\nTrain {tr_acc:.4f} | Test {te_acc:.4f} | gap {tr_acc-te_acc:+.4f}")
