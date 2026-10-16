import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from sklearn.preprocessing import LabelEncoder

def preprocess(df):
    # Handle Cabin: split into deck, num, side
    df['Cabin'] = df['Cabin'].fillna('Unknown/Unknown/Unknown')
    df[['Deck', 'CabinNum', 'Side']] = df['Cabin'].str.split('/', expand=True)
    
    # Fill missing values
    # Categorical: mode
    cat_cols = ['HomePlanet', 'CryoSleep', 'Destination', 'VIP', 'Deck', 'Side']
    for col in cat_cols:
        df[col] = df[col].fillna(df[col].mode()[0])
    
    # Numerical: median
    num_cols = ['Age', 'RoomService', 'FoodCourt', 'ShoppingMall', 'Spa', 'VRDeck']
    for col in num_cols:
        df[col] = df[col].fillna(df[col].median())
    
    # Encode categorical
    le = LabelEncoder()
    for col in cat_cols:
        df[col] = le.fit_transform(df[col].astype(str))
    
    # Drop original Cabin column
    if 'Cabin' in df.columns:
        df = df.drop('Cabin', axis=1)
    
    # Ensure CabinNum is numeric
    if 'CabinNum' in df.columns:
        df['CabinNum'] = pd.to_numeric(df['CabinNum'], errors='coerce').fillna(0)
    
    return df

# Load data
train = pd.read_csv('data/train.csv')
test = pd.read_csv('data/test.csv')

# Save PassengerIds for the final output
test_ids = test['PassengerId']

# Drop identifiers
train_df = train.drop(['PassengerId', 'Name'], axis=1)
test_df = test.drop(['PassengerId', 'Name'], axis=1)

# Separate target
y = train_df['Transported']
X = train_df.drop('Transported', axis=1)

# Preprocess X and test_df
X = preprocess(X)
test_df = preprocess(test_df)

# Split for validation
X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42)

# Train model
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# Validate
val_preds = model.predict(X_val)
accuracy = accuracy_score(y_val, val_preds)
print(f"Validation Accuracy: {accuracy:.4f}")

# Final predictions on test set
predictions = model.predict(test_df)
submission = pd.DataFrame({'PassengerId': test_ids, 'Transported': predictions})
submission.to_csv('predictions.csv', index=False)
