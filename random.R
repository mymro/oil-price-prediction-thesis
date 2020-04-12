
sum_profit = 0
sum_max_value = 0
rounds = 100000

for(i in 1:rounds){
  max_value = 0
  barrels = 0
  value = 0
  profit = 0
  
  for(index in 3:length(formatted_training_data$WTI)){
    current_price = formatted_training_data$WTI[index]
    if(round(runif(1)) == 1){
      barrels = barrels + 1
      value = value + current_price
      if(value > max_value){
        max_value = value
      }
    }else{
      profit = profit + barrels * current_price - value
      barrels = 0
      value = 0
    }
  }
  
  sum_profit = sum_profit + profit
  sum_max_value = sum_max_value + max_value
}

print(sum_profit/rounds)
print(sum_max_value/rounds)