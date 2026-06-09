import lightgbm as lgb


def build_aggregates(df):
    city_eta = df.groupby("city_name")["actual_eta_min"].mean().to_dict()
    type_eta = df.groupby("typecode")["actual_eta_min"].mean().to_dict()
    aoi_eta = df.groupby("aoi_id")["actual_eta_min"].mean().to_dict()

    courier_avg_eta = df.groupby("delivery_user_id")["actual_eta_min"].mean().to_dict()
    courier_total_orders = df.groupby("delivery_user_id").size().to_dict()

    df["city_avg_eta"] = df["city_name"].map(city_eta)
    df["type_avg_eta"] = df["typecode"].map(type_eta)
    df["aoi_avg_eta"] = df["aoi_id"].map(aoi_eta)
    df["courier_avg_eta"] = df["delivery_user_id"].map(courier_avg_eta)
    df["courier_total_orders"] = df["delivery_user_id"].map(courier_total_orders)

    return df, city_eta, type_eta, aoi_eta, courier_avg_eta, courier_total_orders


def encode(df):
    from sklearn.preprocessing import LabelEncoder

    label_encoders = {}

    for col in ["city_name", "typecode"]:
        le = LabelEncoder()
        vals = df[col].astype(str)
        le.fit(vals)

        df[col + "_enc"] = le.transform(vals)
        label_encoders[col] = le

    aoi_map = {v: i for i, v in enumerate(df["aoi_id"].astype(str).unique())}

    df["aoi_id_enc"] = (
        df["aoi_id"].astype(str)
        .map(aoi_map)
        .fillna(-1)
        .astype(int)
    )

    return df, label_encoders, aoi_map


def train_model(X_train, y_train, X_test, y_test, params, feature_cols, num_round, early_stop):
    lgb_train = lgb.Dataset(X_train, y_train, feature_name=feature_cols)
    lgb_val = lgb.Dataset(X_test, y_test, feature_name=feature_cols, reference=lgb_train)

    model = lgb.train(
        params,
        lgb_train,
        num_boost_round=num_round,
        valid_sets=[lgb_val],
        valid_names=["validation"],
        callbacks=[
            lgb.early_stopping(early_stop),
            lgb.log_evaluation(50),
        ],
    )

    return model
