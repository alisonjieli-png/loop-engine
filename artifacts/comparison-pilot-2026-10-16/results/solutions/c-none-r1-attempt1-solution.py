import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from sklearn.preprocessing import LabelEncoder

def preprocess(df):
    # Drop columns that aren't useful for prediction
    df = df.drop(['PassengerId', 'Name'], axis=1)
    
    # Split Cabin into deck, num, side
    df[['Deck', 'CabinNum', 'Side']] = df['Cabin'].str.split('/', expand=True)
    df = df.drop('Cabin', axis=1)
    
    # Convert CabinNum to numeric
    df['CabinNum'] = pd.to_numeric(df['CabinNum'], errors='coerce')
    
    # Fill missing values
    # Categorical
    cat_cols = ['HomePlanet', 'CryoSleep', 'Destination', 'VIP', 'Deck', 'Side']
    for col in cat_cols:
        df[col] = df[col].fillna(df[col].mode()[0])
    
    # Numerical
    num_cols = ['Age', 'RoomService', 'FoodCourt', 'ShoppingMall', 'Spa', 'VRDeck', 'CabinNum']
    for col in num_cols:
        df[col] = df[col].fillna(df[col].median())
    
    # Encode categorical
    le = LabelEncoder()
    for col in cat_cols:
        df[col] = le.fit_transform(df[col].astype(str))
        
    return df

def main():
    train_df = pd.read_csv('data/train.csv')
    test_df = pd.read_csv('data/test.csv')
    
    passenger_ids = test_df['PassengerId']
    
    y = train_df['Transported']
    X = train_df.drop('Transported', axis=1)
    
    # Preprocess X and test_df
    # We need to handle them together or ensure same encoding
    combined = pd.concat([X, test_df], axis=0).reset_index(drop=True)
    
    # Process combined to ensure consistent encoding
    processed_combined = preprocess(combined.copy())
    
    X_processed = processed_combined.iloc[:len(train_df)]
    X_test_processed = processed_combined.iloc[len(train_df):]
    
    X_train, X_val, y_train, y_val = train_test_split(X_processed, y, test_size=0.2, random_state=42)
    
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    
    val_preds = model.predict(X_val)
    acc = accuracy_score(y_val, val_preds)
    print(f"Validation Accuracy: {acc:.4f}")
    
    test_preds = model.predict(X_test_processed)
    
    predictions = pd.DataFrame({
        'PassengerId': passenger_ids,
        'Transported': test_preds
    })
    
    predictions.to_csv('predictions.csv', index=False)

if __name__ == "__main__":
    main()
