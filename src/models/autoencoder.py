"""Feed-forward autoencoder trained on legitimate training rows only.

Early stopping uses an internal slice of the AE training data. The global
validation split remains reserved for detector model selection and thresholding.
"""

import numpy as np
import tensorflow as tf
from tensorflow import keras


def build_autoencoder(
    input_dim: int,
    hidden=(20,),
    bottleneck: int = 10,
    lr: float = 1e-3,
    seed: int = 42,
) -> keras.Model:
    """Build and compile a symmetric dense autoencoder."""
    if input_dim <= 0 or bottleneck <= 0:
        raise ValueError("input_dim and bottleneck must be positive")
    tf.keras.utils.set_random_seed(seed)
    inputs = keras.Input(shape=(input_dim,))
    values = inputs
    for width in hidden:
        values = keras.layers.Dense(width, activation="relu")(values)
    values = keras.layers.Dense(
        bottleneck,
        activation="relu",
        name="bottleneck",
    )(values)
    for width in reversed(hidden):
        values = keras.layers.Dense(width, activation="relu")(values)
    outputs = keras.layers.Dense(input_dim, activation="linear")(values)
    model = keras.Model(inputs, outputs)
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=lr),
        loss="mse",
    )
    return model


def train_autoencoder(
    model: keras.Model,
    X_train_legit: np.ndarray,
    epochs: int = 50,
    batch_size: int = 256,
    patience: int = 5,
    ae_val_frac: float = 0.1,
    seed: int = 42,
) -> keras.Model:
    """Train using an internal validation slice of training-legitimate rows."""
    values = np.asarray(X_train_legit, dtype="float32")
    if len(values) < 2:
        raise ValueError("autoencoder training requires at least two rows")
    if not 0 < ae_val_frac < 1:
        raise ValueError("ae_val_frac must be between zero and one")

    rng = np.random.default_rng(seed)
    indices = rng.permutation(len(values))
    validation_size = max(1, int(len(indices) * ae_val_frac))
    if validation_size >= len(indices):
        validation_size = len(indices) - 1
    validation_indices = indices[:validation_size]
    training_indices = indices[validation_size:]
    early_stopping = keras.callbacks.EarlyStopping(
        monitor="val_loss",
        patience=patience,
        restore_best_weights=True,
    )
    model.fit(
        values[training_indices],
        values[training_indices],
        validation_data=(
            values[validation_indices],
            values[validation_indices],
        ),
        epochs=epochs,
        batch_size=batch_size,
        callbacks=[early_stopping],
        verbose=0,
        shuffle=True,
    )
    return model


def reconstruction_error(model: keras.Model, X: np.ndarray) -> np.ndarray:
    """Return per-row mean squared reconstruction error."""
    values = np.asarray(X, dtype="float32")
    reconstruction = model.predict(values, verbose=0)
    return np.mean((values - reconstruction) ** 2, axis=1)


def latent_features(model: keras.Model, X: np.ndarray) -> np.ndarray:
    """Return bottleneck activations for each row."""
    encoder = keras.Model(
        model.inputs,
        model.get_layer("bottleneck").output,
    )
    return encoder.predict(np.asarray(X, dtype="float32"), verbose=0)
