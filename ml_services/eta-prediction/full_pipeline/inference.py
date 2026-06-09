# =============================================================================
# ETA PREDICTOR CLASS
# =============================================================================
import numpy as np
import pandas as pd
import pickle

class ETAPredictor:

    """
    Serializable ETA prediction bundle.
    """

    def __init__(
        self,
        model,
        feature_cols,
        label_encoders,
        aoi_map,
        city_eta,
        type_eta,
        aoi_eta,
        courier_avg_eta,
        courier_total_orders,
        version="2.0",
    ):
        self.model = model

        self.feature_cols = feature_cols

        self.label_encoders = label_encoders

        self.aoi_map = aoi_map

        self.city_eta = city_eta

        self.type_eta = type_eta

        self.aoi_eta = aoi_eta

        self.courier_avg_eta = courier_avg_eta

        self.courier_total_orders = courier_total_orders

        self.version = version

    # =========================================================================
    # FEATURE PREP
    # =========================================================================

    def prepare_features(
        self,
        orders_df,
    ):

        df = orders_df.copy()

        # ---------------------------------------------------------------------
        # TIME FEATURES
        # ---------------------------------------------------------------------

        df["receipt_time"] = pd.to_datetime(
            df["receipt_time"]
        )

        df["hour_of_day"] = (
            df["receipt_time"].dt.hour
        )

        df["minute"] = (
            df["receipt_time"].dt.minute
        )

        df["day_of_week"] = (
            df["receipt_time"].dt.dayofweek
        )

        df["month"] = (
            df["receipt_time"].dt.month
        )

        df["is_morning"] = (
            df["hour_of_day"] < 12
        ).astype(np.int8)

        df["is_afternoon"] = (
            (df["hour_of_day"] >= 12)
            & (df["hour_of_day"] < 17)
        ).astype(np.int8)

        df["is_evening"] = (
            df["hour_of_day"] >= 17
        ).astype(np.int8)

        # ---------------------------------------------------------------------
        # DISTANCE FEATURES
        # ---------------------------------------------------------------------

        dlat = (
            df["poi_lat"]
            - df["receipt_lat"]
        )

        dlng = (
            df["poi_lng"]
            - df["receipt_lng"]
        )

        df["euclidean_dist"] = np.sqrt(
            dlat**2 + dlng**2
        )

        df["manhattan_dist"] = (
            np.abs(dlat)
            + np.abs(dlng)
        )

        df["log_distance"] = np.log1p(
            df["euclidean_dist"]
        )

        bearing = np.arctan2(
            dlng,
            dlat,
        )

        df["bearing_sin"] = np.sin(
            bearing
        )

        df["bearing_cos"] = np.cos(
            bearing
        )

        # ---------------------------------------------------------------------
        # DEFAULT ROUTE FEATURES
        # ---------------------------------------------------------------------

        if "stop_rank" not in df.columns:
            df["stop_rank"] = 0

        if "stops_remaining" not in df.columns:
            df["stops_remaining"] = 1

        df["receipt_hour"] = (
            df["receipt_time"].dt.hour
        )

        if "wait_since_first_order_min" not in df.columns:
            df["wait_since_first_order_min"] = 0.0

        df["log_wait_since_first_order"] = np.log1p(
            df["wait_since_first_order_min"]
        )

        # ---------------------------------------------------------------------
        # ENCODERS
        # ---------------------------------------------------------------------

        for col in [
            "city_name",
            "typecode",
        ]:

            le = self.label_encoders[col]

            known = set(le.classes_)

            df[col + "_enc"] = (
                df[col]
                .astype(str)
                .map(
                    lambda x: (
                        int(le.transform([x])[0])
                        if x in known
                        else -1
                    )
                )
            )

        df["aoi_id_enc"] = (
            df["aoi_id"]
            .astype(str)
            .map(self.aoi_map)
            .fillna(-1)
            .astype(np.int32)
        )

        # ---------------------------------------------------------------------
        # HISTORICAL FEATURES
        # ---------------------------------------------------------------------

        df["city_avg_eta"] = (
            df["city_name"]
            .map(self.city_eta)
            .fillna(45)
        )

        df["type_avg_eta"] = (
            df["typecode"]
            .map(self.type_eta)
            .fillna(45)
        )

        df["aoi_avg_eta"] = (
            df["aoi_id"]
            .map(self.aoi_eta)
            .fillna(45)
        )

        df["courier_avg_eta"] = (
            df["delivery_user_id"]
            .map(self.courier_avg_eta)
            .fillna(45)
        )

        df["courier_total_orders"] = (
            df["delivery_user_id"]
            .map(self.courier_total_orders)
            .fillna(1)
        )

        return df

    # =========================================================================
    # PREDICT ETA
    # =========================================================================

    def predict_eta(
        self,
        orders_df,
    ):

        feat_df = self.prepare_features(
            orders_df
        )

        X = feat_df[self.feature_cols]

        preds = self.model.predict(
            X,
            num_iteration=self.model.best_iteration,
        )

        preds = np.clip(
            preds,
            1,
            480,
        )

        return preds

    # =========================================================================
    # SAVE
    # =========================================================================

    def save(
        self,
        path,
    ):

        with open(path, "wb") as f:
            pickle.dump(
                self,
                f,
                protocol=pickle.HIGHEST_PROTOCOL,
            )

        print(f"Saved model -> {path}")

    # =========================================================================
    # LOAD
    # =========================================================================

    @classmethod
    def load(
        cls,
        path,
    ):

        with open(path, "rb") as f:
            obj = pickle.load(f)

        return obj
