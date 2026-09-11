import numpy as np
from sklearn.linear_model import LinearRegression


def train_local_model(patient_counts):

    if len(patient_counts) < 2:
        return None

    X = np.array(
        range(1, len(patient_counts) + 1)
    ).reshape(-1, 1)

    y = np.array(patient_counts)

    model = LinearRegression()

    model.fit(X, y)

    return {
        "coefficient": float(model.coef_[0]),
        "intercept": float(model.intercept_),
        "data_points": len(patient_counts)
    }


def federated_average(local_models):

    if not local_models:
        return None

    total_data = sum(
        model["data_points"]
        for model in local_models
    )

    weighted_coefficient = sum(
        model["coefficient"] *
        model["data_points"]
        for model in local_models
    ) / total_data

    weighted_intercept = sum(
        model["intercept"] *
        model["data_points"]
        for model in local_models
    ) / total_data

    return {
        "global_coefficient": round(
            weighted_coefficient,
            4
        ),

        "global_intercept": round(
            weighted_intercept,
            4
        ),

        "participating_phcs": len(
            local_models
        ),

        "total_data_points": total_data
    }