Optimize this fraud scoring function for latency and explain any bugs:
import numpy as np
def fraud_score(txn):
    features = extract(txn)
    return model.predict(features)[0]
