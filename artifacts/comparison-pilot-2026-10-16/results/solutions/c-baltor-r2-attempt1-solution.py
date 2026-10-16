import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from sklearn.preprocessing import LabelEncoder

def preprocess(df):
    # Fill numeric NaNs with median
    numeric_cols = ['Age', 'RoomService', 'FoodCourt', 'ShoppingMall', 'Spa', 'VRDeck']
    for col in numeric_cols:
        df[col] = df[col].fillna(df[col].median())
    
    # Fill categorical NaNs with mode
    categorical_cols = ['HomePlanet', 'CryoSleep', 'Destination', 'VIP']
    for col in categorical_cols:
        df[col] = df[col].fillna(df[col].mode()[0])
    
    # Feature Engineering: Cabin
    # Cabin is deck/num/side
    df['Cabin'] = df['Cabin'].fillna('Unknown/Unknown/Unknown')
    df['Deck'] = df['Cabin'].apply(lambda x: x.split('/')[0])
    df['CabinSide'] = df['Cabin'].apply(lambda x: x.split('/')[-1])
    
    # Feature Engineering: Total Spending
    spending_cols = ['RoomService', 'FoodCourt', 'ShoppingMall', 'Spa', 'VRDeck']
    df['TotalSpending'] = df[spending_cols].sum(axis=1)
    
    # Drop unnecessary columns
    df = df.drop(['PassengerId', 'Name', 'Cabin'], axis=1)
    
    # Encode categorical variables
    le = LabelEncoder()
    cat_features = ['HomePlanet', 'CryoSleep', 'Destination', 'VIP', 'Deck', 'CabinSide']
    for col in cat_features:
        df[col] = le.fit_transform(df[col].astype(str))
        
    return df

# Load data
train_df = pd.read_csv('data/train.csv')
test_df = pd.read_csv('data/test.csv')

# Save PassengerIds for final submission
test_ids = test_df['PassengerId']

# Target
y = train_df['Transported'].astype(int)
X = train_df.drop('Transported', axis=1)

# Preprocess train and test separately to avoid leakage if using medians from test
# But typically we apply train medians to test. 
# For simplicity in this script, we preprocess them together or separately.
# Let's do it together to keep it simple, but standard is train-based.

all_data = pd.concat([X, test_df], axis=0)
all_data_processed = preprocess(all_data)

X_processed = all_data_processed.iloc[:len(train_df), :]
X_test_processed = all_data_processed.iloc[len(train_df):, :]

# Validation split
X_train, X_val, y_train, y_val = train_test_split(X_processed, y, test_size=0.2, random_state=42)

# Model
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# Validation accuracy
val_preds = model.predict(X_val)
acc = accuracy_score(y_val, val_preds)
print(f"Validation Accuracy: {acc:.4f}")

# Final predictions for test.csv
test_preds = model.predict(X_test_processed)
predictions = pd.DataFrame({
    'PassengerId': test_ids,
    'Transported': test_preds.astype(bool)
})

predictions.to_csv('predictions.csv', index=False)
