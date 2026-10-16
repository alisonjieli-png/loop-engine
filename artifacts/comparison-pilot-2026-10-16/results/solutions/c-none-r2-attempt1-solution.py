import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score

def preprocess(df):
    # Drop Name as it is likely unique and not helpful
    df = df.drop(columns=['Name'])
    
    # Feature Engineering: Cabin
    # Cabin is deck/num/side
    df[['CabinDeck', 'CabinNum', 'CabinSide']] = df['Cabin'].str.split('/', expand=True)
    df = df.drop(columns=['Cabin'])
    
    # Fill missing values
    # For categorical, use mode
    cat_cols = df.select_dtypes(include=['object']).columns
    for col in cat_cols:
        df[col] = df[col].fillna(df[col].mode()[0])
        
    # For numerical, use median
    num_cols = df.select_dtypes(include=['float64', 'int64']).columns
    for col in num_cols:
        df[col] = df[col].fillna(df[col].median())
        
    # Encode categorical
    le = LabelEncoder()
    for col in cat_cols:
        df[col] = le.fit_transform(df[col].astype(str))
        
    return df

# Load data
train = pd.read_csv('data/train.csv')
test = pd.read_csv('data/test.csv')

# Separate target
X = train.drop(columns=['Transported', 'PassengerId'])
y = train['Transported']
X_test_final = test.drop(columns=['PassengerId'])
passenger_ids = test['PassengerId']

# Combine for consistent preprocessing
all_data = pd.concat([X, X_test_final], axis=0)
all_data_proc = preprocess(all_data)

# Split back
X_proc = all_data_proc.iloc[:len(X), :]
X_test_proc = all_data_proc.iloc[len(X):, :]

# Validation split
X_train, X_val, y_train, y_val = train_test_split(X_proc, y, test_size=0.2, random_state=42)

# Model
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# Validation accuracy
val_preds = model.predict(X_val)
acc = accuracy_score(y_val, val_preds)
print(f"Validation Accuracy: {acc:.4f}")

# Final predictions
final_preds = model.predict(X_test_proc)
output = pd.DataFrame({'PassengerId': passenger_ids, 'Transported': final_preds})
output.to_csv('predictions.csv', index=False)
