import numpy as np
import pytest

from src.models.autoencoder import (
    build_autoencoder,
    latent_features,
    reconstruction_error,
    train_autoencoder,
)


def test_ae_reconstruction_error_flags_outliers():
    rng = np.random.default_rng(0)
    normal = rng.normal(0, 1, (600, 8)).astype("float32")
    outliers = rng.normal(8, 1, (30, 8)).astype("float32")
    autoencoder = build_autoencoder(
        input_dim=8,
        hidden=(6,),
        bottleneck=3,
        seed=42,
    )

    train_autoencoder(
        autoencoder,
        normal,
        epochs=30,
        batch_size=64,
        seed=42,
    )

    normal_error = reconstruction_error(autoencoder, normal)
    outlier_error = reconstruction_error(autoencoder, outliers)
    assert outlier_error.mean() > normal_error.mean() * 2


def test_latent_features_shape():
    rng = np.random.default_rng(0)
    values = rng.normal(size=(50, 8)).astype("float32")
    autoencoder = build_autoencoder(
        input_dim=8,
        hidden=(6,),
        bottleneck=3,
        seed=42,
    )

    assert latent_features(autoencoder, values).shape == (50, 3)


def test_autoencoder_internal_validation_contract_rejects_bad_fraction():
    autoencoder = build_autoencoder(input_dim=2, bottleneck=1)
    with pytest.raises(ValueError, match="between zero and one"):
        train_autoencoder(
            autoencoder,
            np.zeros((10, 2), dtype="float32"),
            ae_val_frac=1.0,
        )


def test_autoencoder_internal_validation_uses_only_supplied_training_rows():
    class RecordingModel:
        def __init__(self):
            self.fit_call = None

        def fit(self, X, y, **kwargs):
            self.fit_call = (X.copy(), y.copy(), kwargs)

    model = RecordingModel()
    values = np.arange(40, dtype="float32").reshape(20, 2)

    train_autoencoder(
        model,
        values,
        epochs=1,
        batch_size=4,
        ae_val_frac=0.2,
        seed=42,
    )

    X_train, y_train, kwargs = model.fit_call
    X_val, y_val = kwargs["validation_data"]
    assert len(X_train) == len(y_train) == 16
    assert len(X_val) == len(y_val) == 4
    supplied_rows = {tuple(row) for row in values}
    training_rows = {tuple(row) for row in X_train}
    validation_rows = {tuple(row) for row in X_val}
    assert training_rows.issubset(supplied_rows)
    assert validation_rows.issubset(supplied_rows)
    assert training_rows.isdisjoint(validation_rows)
