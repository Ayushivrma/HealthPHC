import numpy as np
from sklearn.linear_model import LinearRegression


def forecast_next_days(
    patient_counts,
    days=7
):

    if len(patient_counts) < 2:
        return None

    X = np.array(
        range(
            1,
            len(patient_counts) + 1
        )
    ).reshape(-1, 1)

    y = np.array(patient_counts)

    model = LinearRegression()

    model.fit(X, y)

    future_days = np.array(
        range(
            len(patient_counts) + 1,
            len(patient_counts) + days + 1
        )
    ).reshape(-1, 1)

    predictions = model.predict(
        future_days
    )

    return [
        max(
            0,
            round(float(value), 2)
        )
        for value in predictions
    ]