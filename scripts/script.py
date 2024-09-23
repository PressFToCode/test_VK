"""
Скрипт обрабатывает логи из указанной директории и возвращает 
агрегированные данные о количестве действий каждого пользователя 
за указанный период.

Пример запуска скрипта:
python3 script.py 2024-09-10

"""


import sys
import os
from datetime import datetime, timedelta
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, count


# Инициализация сессии Apache Spark
spark = SparkSession.builder \
    .appName("WeeklyAggregation") \
    .getOrCreate()

def process_logs_with_cache(start_date, end_date, input_dir, cache_dir):
    """
    Функция обрабатывает логи из указанной директории за указанный период,
    агрегируя данные о количестве действий каждого пользователя.
    
    Для ускорения работы функция использует кэширование промежуточных данных 
    в формате Apache Parquet. Если кэш для дня уже существует, то функция 
    загружает его, иначе - загружает данные из исходного CSV, обрабатывает 
    их и сохраняет кэш.
    
    :param start_date: дата начала периода
    :param end_date: дата конца периода
    :param input_dir: директория, где хранятся логи
    :param cache_dir: директория, где хранится кэш
    :return: DataFrame, содержащий агрегированные данные
    """
    data = []

    for day in range((end_date - start_date).days):
        current_date = start_date + timedelta(days=day)
        day_str = current_date.strftime("%Y-%m-%d")
        
        # Проверяем, существует ли промежуточный файл
        cache_path = os.path.join(cache_dir, f"{day_str}.parquet")
        if os.path.exists(cache_path):
            # Загружаем промежуточные данные
            df = spark.read.parquet(cache_path)
        else:
            # Если данных нет, загружаем из исходного CSV и сохраняем
            file_path = os.path.join(input_dir, f"{day_str}.csv")
            if os.path.exists(file_path):
                df = spark.read.csv(file_path, header=False, inferSchema=True)
                df = df.withColumnRenamed("_c0", "email") \
                       .withColumnRenamed("_c1", "action") \
                       .withColumnRenamed("_c2", "dt")
                df.write.parquet(cache_path)
            else:
                continue
        
        agg_df = df.groupBy("email", "action").count()
        data.append(agg_df)

    if data:
        result_df = data[0]
        for df in data[1:]:
            result_df = result_df.union(df)

        result_df = result_df.groupBy("email").pivot("action").agg(count("action"))
        result_df = result_df.na.fill(0)
        return result_df

    return None

def main():
    """
    Главная функция, которая получает из командной строки дату,
    считывает логи за неделю, предшествующую указанной дате,
    вычисляет агрегаты и пишет их в файл.
    """
    if len(sys.argv) != 2:
        print("Usage: python script.py <YYYY-mm-dd>")
        sys.exit(1)

    input_date = datetime.strptime(sys.argv[1], "%Y-%m-%d")
    start_date = input_date - timedelta(days=7)
    input_dir = "../input"
    output_dir = "../output"
    cache_dir = "../intermediate"

    # Вычисление агрегатов
    result_df = process_logs_with_cache(start_date, input_date, input_dir, cache_dir)
    
    if result_df:
        output_path = os.path.join(output_dir, f"{input_date.strftime('%Y-%m-%d')}.csv")
        result_df.coalesce(1).write.csv(output_path, header=True)
        print(f"Aggregated data saved to {output_path}")
    else:
        print("No data to process.")

if __name__ == "__main__":
    main()
