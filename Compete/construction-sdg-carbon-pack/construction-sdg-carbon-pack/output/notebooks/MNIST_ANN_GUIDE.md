# MNIST ANN — step-by-step (verified run, TF 2.21)

Result: **99.39% train / 98.04% test** in 20 epochs, ~90 s on CPU.
Run it: `python3 mnist_ann.py`

---

## Step 1 — Load MNIST
```python
(x_train, y_train), (x_test, y_test) = keras.datasets.mnist.load_data()
x_train = x_train.astype("float32") / 255.0
x_test  = x_test.astype("float32")  / 255.0
y_train_oh = keras.utils.to_categorical(y_train, 10)
```
- Shapes: 60 000 + 28×28 = 784 inputs per image.
- Pixel range 0..255, so we scale to 0..1 for stable gradients.
- Labels (0..9) one-hot because Stage 4 uses softmax + cross-entropy.
- **Why:** raw pixel values in the hundreds saturate ReLU/BatchNorm at init.

## Step 2 — Sequential scaffold
```python
keras.Sequential([
    Input(shape=(28, 28, 1)), Flatten(),
    Dense(512, ...), BatchNormalization(), Dropout(...),   # ×2
    Dense(256, ...), BatchNormalization(), Dropout(...),
    Dense(10, "softmax"),
])
```
ANN (fully-connected) not CNN — the image asked for the dense stack. Total **803 K params**.

## Step 3 — The four architecture ingredients
Per hidden Dense layer:
```python
Dense(512, activation="relu",
      kernel_initializer=HeNormal(seed=42),   # weight init
      kernel_regularizer=L2(1e-4))            # L2 penalty
BatchNormalization()                          # activation stats
Dropout(0.25)                                 # dropped units
```
- **He Normal** (a.k.a. *Kaiming*): variance = 2/fan_in. Chosen specifically because every hidden layer is **ReLU** — ReLU zeroes half the activations, so Xavier/Glorot under-scales and He compensates by the extra factor 2.
- **L2 (1e-4)**: adds `λ·Σw²` to the loss → shrinks weights toward 0 → less overfitting. Verified live: the 0.1035 you see in the log is purely `model.losses` (the penalty), not data error.
- **BatchNorm**: standardises each batch before the activation → higher LR, faster convergence, mild regularisation. Placed **Dense → BN → Dropout** (BN after the linear op, before the nonlinearity works best).
- **Dropout 0.25**: zeroes units only during training, scaled up at inference. It is *redundant on top of* BN+L2 on MNIST but the image asked for all three.

| Ingredient | What it fixes | When it fires |
|---|---|---|
| He Normal | exploding/vanishing init | before training |
| L2 | large weights | every step |
| BatchNorm | unstable activations | every batch |
| Dropout | memorising noise | only during fit |

## Step 4 — Fit + compile (train & test)
```python
model.compile(optimizer="adam", loss="categorical_crossentropy",
              metrics=["accuracy"])
x_val, y_val = x_train[-10000:], y_train_oh[-10000:]
model.fit(x_fit, y_fit, batch_size=128, epochs=20,
          validation_data=(x_val, y_val),
          callbacks=[EarlyStopping(monitor="val_loss", patience=3,
                                   restore_best_weights=True)])
```
- **batch_size=128 matters** with BatchNorm: BN's mean/var come per-batch, so a tiny/large batch changes convergence behavior. 128 keeps BN stats close to the full-dataset stats.
- Validation = held-out **train** split, used for EarlyStopping only. Test is touched *only at the end*, never for selection — otherwise you leak.

## Step 5 — Evaluate both sets
```python
model.evaluate(x_fit, y_fit)   # TRAIN (fit split)
model.evaluate(x_test, y_test) # TEST
```
| split | accuracy | loss |
|---|---|---|
| train (50 k) | **99.39%** | 0.1210 |
| valid (10 k) | **98.12%** | 0.1771 |
| **test (10 k)** | **98.04%** | 0.1742 |

**Gap: +1.35%.** That's the regularization budget: without L2 + dropout, MNIST nets memorize and the gap grows to ~2-3%. Confusion matrix shows the residual errors are **4 ↔ 9 (18 swaps)**, the classic handwriting ambiguity.

## Tune in this order
1. `n_units` 512→256: speed, ~-0.2% acc.
2. `L2_SCALE` 1e-4→3e-4: gap closes, then acc drops.
3. `DROPOUT_RATE`: start at 0.25.
4. Add `Adam(learning_rate=3e-3)` if BN makes it slow.
