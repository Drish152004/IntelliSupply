(venv) PS C:\Users\Relanto\Desktop\intellisupply\IntelliSupply\ml_services\eta-prediction> python train_and_evaluate_eta_pipeline.py

==============================
LOADING DELIVERY DATA
==============================
Loaded rows: 472,419
After filtering: 444,085
Dropped: 28,334

==============================
COMPUTING HISTORICAL STATS
==============================

==============================
TEMPORAL SPLIT
==============================
Unique ds values : 15
Cutoff ds        : 330
Train rows: 357,547
Test rows : 86,538

==============================
TRAINING MATRICES
==============================
X_train: (357547, 29)
X_test : (86538, 29)

==============================
TRAINING LIGHTGBM ETA MODEL
==============================
Training until validation scores don't improve for 100 rounds
[50]    validation's l1: 35.0105
[100]   validation's l1: 29.782
[150]   validation's l1: 28.3332
[200]   validation's l1: 27.7396
[250]   validation's l1: 27.4053
[300]   validation's l1: 27.2117
[350]   validation's l1: 27.0634
[400]   validation's l1: 26.952
[450]   validation's l1: 26.8869
[500]   validation's l1: 26.8331
[550]   validation's l1: 26.7906
[600]   validation's l1: 26.7383
[650]   validation's l1: 26.7088
[700]   validation's l1: 26.6877
[750]   validation's l1: 26.6671
[800]   validation's l1: 26.6457
[850]   validation's l1: 26.6266
[900]   validation's l1: 26.6167
[950]   validation's l1: 26.6089
[1000]  validation's l1: 26.5958
[1050]  validation's l1: 26.5912
[1100]  validation's l1: 26.5865
[1150]  validation's l1: 26.5804
[1200]  validation's l1: 26.5855
Did not meet early stopping. Best iteration is:
[1160]  validation's l1: 26.5787

==============================
RUNNING PREDICTIONS
==============================

==============================
ETA METRICS
==============================
MAE  : 26.57 minutes
RMSE : 40.28 minutes
MAPE : 42.56%

Within 10 min : 32.08%
Within 20 min : 55.74%
Within 30 min : 70.71%

==============================
FEATURE IMPORTANCE
==============================
                       feature  importance
19  wait_since_first_order_min       24644
27             courier_avg_eta       23696
28        courier_total_orders       22928
10                      minute       21853
17             stops_remaining       19486
16                   stop_rank       17379
23                  aoi_id_enc       16297
26                 aoi_avg_eta       15860
1                      poi_lng       14833
7                  bearing_sin       14799
8                  bearing_cos       14456
11                 day_of_week       13708
0                      poi_lat       13616
4               euclidean_dist       12454
5               manhattan_dist       11149
2                  receipt_lat       10600
3                  receipt_lng       10598
9                  hour_of_day        7505
20  log_wait_since_first_order        2575
22                typecode_enc        2497
25                type_avg_eta        1349
6                 log_distance        1081
18                receipt_hour         753
14                is_afternoon         374
13                  is_morning          79
21               city_name_enc          45
15                  is_evening          24
24                city_avg_eta           2
12                       month           0

==============================
SAMPLE PREDICTIONS
==============================
    actual_eta_min  predicted_eta_min  absolute_error
0             50.0          19.452469       30.547531
1             74.0          37.823186       36.176814
2             82.0          59.138033       22.861967
3             91.0          77.059790       13.940210
4             97.0          89.571579        7.428421
5            104.0          99.732744        4.267256
6            115.0         113.180316        1.819684
7            126.0         122.888084        3.111916
8            128.0         123.578381        4.421619
9            137.0         136.713613        0.286387
10           145.0         146.858845        1.858845
11           164.0         161.157863        2.842137
12            31.0          48.874037       17.874037
13            38.0          50.183730       12.183730
14           220.0         193.305158       26.694842
15            54.0          33.352001       20.647999
16            61.0          35.362415       25.637585
17             8.0          29.506997       21.506997
18           108.0          50.056593       57.943407
19           118.0          50.773006       67.226994

==============================
WORST PREDICTIONS
==============================
       actual_eta_min  predicted_eta_min  absolute_error
71112           450.0          82.703712      367.296288
21445           438.0          70.833515      367.166485
61              409.0          42.441401      366.558599
35959           400.0          38.101812      361.898188
54225           421.0          77.113107      343.886893
14089           461.0         121.047924      339.952076
84440           422.0          90.672363      331.327637
84439           410.0          84.836076      325.163924
51800           491.0         169.800444      321.199556
35891           435.0         115.573917      319.426083
84278           491.0         175.364722      315.635278
84441           428.0         113.965999      314.034001
43576           424.0         112.798629      311.201371
71821           462.0         152.145580      309.854420
29234           432.0         124.543103      307.456897
16097           439.0         131.647648      307.352352
13022           471.0         164.115529      306.884471
84442           435.0         129.743757      305.256243
39926           479.0         176.722738      302.277262
62446           410.0         107.955059      302.044941

==============================
ROUTE LEVEL ANALYSIS
==============================
Route-level MAE: 23.14 minutes
Saved model -> C:\Users\Relanto\Desktop\intellisupply\IntelliSupply\ml_services\eta-prediction\eta_lightgbm_model.pkl

==============================
MODEL SAVED
==============================
Saved model -> C:\Users\Relanto\Desktop\intellisupply\IntelliSupply\ml_services\eta-prediction\eta_lightgbm_model.pkl

==============================
FINAL SUMMARY
==============================
Train rows          : 357,547
Test rows           : 86,538
Features            : 29
Best iteration      : 1160
Final MAE           : 26.57 min
Final RMSE          : 40.28 min
Final MAPE          : 42.56%
Route-level MAE     : 23.14 min

==============================
DETAILED BUCKETED ANALYSIS
==============================

--- ETA BUCKET PERFORMANCE ---
  eta_bucket  count        mae       rmse        mape
0       0-10   1160  34.667141  46.727067  860.998599
1      10-20   3037  20.713953  28.822609  134.868821
2      20-30   4873  17.309977  24.905461   68.460018
3      30-60  18214  15.927673  23.501751   36.008774
4     60-120  28768  20.825172  28.818602   24.146104
5       120+  30486  40.108755  56.806360   19.368585

--- DISTANCE BUCKET PERFORMANCE ---
Empty DataFrame
Columns: [dist_bucket, count, mae, mape]
Index: []

--- TIME OF DAY PERFORMANCE ---
  time_bucket  count        mae       mape
0       night   1207  22.669175  21.509463
1     morning  47734  26.017655  30.895919
2   afternoon  32967  28.027698  54.307814
3     evening   4625  22.931907  84.634571
4  late_night      5  19.341665  76.394457

--- ROUTE SIZE PERFORMANCE ---
  route_size_bucket  count        mae        mape
0                 1    211  69.769800  287.984829
1               2-3    242  55.362564  173.428837
2               4-5    381  48.972513  100.530773
3              6-10   3208  46.992948   77.132565
4             10-50  76635  25.912376   40.381751
5               50+   5861  19.810337   34.089184

--- WORST ROUTES (TOP 10) ---
                      delivery_user_id   ds         mae  count
1635  660f87e7759d91f23e67c7b3e10d0ef6  331  361.898188      1
578   25c9945c480491a3856b65100e3d1c57  331  306.884471      1
1934  787d22cc997e05094a79b8b0372bc72b  331  292.999206      1
1260  50ffcea849b4bd8e08b9c59e12630df8  401  279.635622      1
3394  dbf40c0814ceb1b8bdb754361b9a9406  330  270.285332      1
1129  4a0436aaf828141e64ea348ae10b6b94  330  258.830685      1
276   112f1de6d98fa90c814a30acd2f26476  331  254.886979      1
3822  f8de9168d15a12376a38328650989826  331  251.033874     12
3829  f999fed96c3f702e7acea10b98a19b50  330  241.432637      1
866   38b5a829e0610c3b3478166e65f1963a  401  240.954701      1

==============================
MAPE STABILITY CHECK
==============================
Short trips MAPE (<=15 min): 513.80%
Long trips MAPE (>60 min)  : 21.69%

==============================
ERROR DISTRIBUTION
==============================
P50 AE : 17.191550437935486
P90 AE : 60.15192524656357
P95 AE : 84.44655884240778
P99 AE : 149.9746962343057
(venv) PS C:\Users\Relanto\Desktop\intellisupply\IntelliSupply\ml_services\eta-prediction> 