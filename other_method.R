library('openxlsx')
library('lubridate')
data <- other_method
data$Date = convertToDateTime(data$Date, origin = "1900-01-01", tz="America/New_York")
data= data[order(data$Date),]

inflation = inflation_data
inflation$TIME = convertToDateTime(inflation$TIME, origin = "1900-01-01", tz="Europe/London")
inflation = inflation[order(inflation$TIME),]
inflation$month = month(inflation$TIME)
inflation$year = year(inflation$TIME)
inflation$days_in_month = days_in_month(inflation$TIME)
days_in_month(inflation$TIME[1])

data$inflation_2015 = NA
data$inflation_rate = NA
for(i in rownames(data)){
  date = data[i,]$Date
  date_prev = as.Date(date) %m-% months(1)
  inflation_d_prev = inflation[inflation$year==year(date_prev) & inflation$month==month(date_prev),]
  inflation_d = inflation[inflation$year==year(date) & inflation$month==month(date),]
  temp = day(date)/inflation_d$days_in_month
  temp2 = inflation_d$Value/inflation_d_prev$Value
  data[i,]$inflation_2015 = inflation_d_prev$Value*((inflation_d$Value/inflation_d_prev$Value)^(day(date)/inflation_d$days_in_month))
  data[i,]$inflation_rate = (inflation_d$Value/inflation_d_prev$Value)^(1/inflation_d$days_in_month)-1
}
#only till 12 2019 after that no inflation data yet
data$real_wti = data$`Cushing, OK WTI Spot Price FOB (Dollars per Barrel)`/(data$inflation_2015/100)

data$wti_log<-log(data$`Cushing, OK WTI Spot Price FOB (Dollars per Barrel)`)
data$oil_log_diff = NA
data$oil_log_diff[1:(nrow(data)-1)] = diff(data$wti_log)
data$weighted = log(data$`heating oil.New York Harbor No. 2 Heating Oil Spot Price FOB (Dollars per Gallon`)
data$diff = data$weighted-data$oil_log_diff

data = na.omit(data)
data$no_change = NA
data$no_change[2:nrow(data)] = data$real_wti[1:nrow(data)-1]

data = na.omit(data)

model = lm(oil_log_diff ~ diff, data=data)
summary(model)

data$predicted = predict(model, data)

data$p_hat = data$real_wti*exp(data$predicted-data$inflation_rate)

data$p_hat_shifted = NA
data$p_hat_shifted[2:nrow(data)] = data$p_hat[1:(nrow(data)-1)]
data = na.omit(data)

pred = sqrt(sum((data$real_wti - data$p_hat_shifted)^2)/nrow(data))
no = sqrt(sum((data$real_wti - data$no_change)^2)/nrow(data))

pred/no

limited_data <- data[data$Date >= "2017-11-18 00:00:00" & data$Date < "2020-02-08",]

pred = sqrt(sum((limited_data$real_wti - limited_data$p_hat_shifted)^2)/nrow(limited_data))
no = sqrt(sum((limited_data$real_wti - limited_data$no_change)^2)/nrow(limited_data))

pred/no

plot(data$Date, data$real_wti, type="l", col="blue")
lines(data$Date, data$p_hat_shifted, col="red", type="l")

plot(limited_data$Date, limited_data$real_wti, type="l", col="blue")
lines(limited_data$Date, limited_data$p_hat_shifted, col="red", type="l")
lines(limited_data$Date, limited_data$no_change, col="green", type="l")

plot(data$Date, data$p_hat_shifted - data$real_wti, type = "l")


sum_profit = 0
sum_max_value = 0
rounds = 10000

for(i in 1:rounds){
  max_value = 0
  barrels = 0
  value = 0
  profit = 0
  
  for(index in 1:length(data$real_wti)){
    current_price = data$`Cushing, OK WTI Spot Price FOB (Dollars per Barrel)`[index]
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
print((sum_profit/rounds)/(sum_max_value/rounds))

sum_profit = 0
sum_max_value = 0
rounds = 1

for(i in 1:rounds){
  max_value = 0
  barrels = 0
  value = 0
  profit = 0
  
  for(index in 1:length(limited_data$real_wti)){
    current_price = limited_data$`Cushing, OK WTI Spot Price FOB (Dollars per Barrel)`[index]
    if(limited_data$p_hat[index] > limited_data$real_wti[index]){
      print("hi")
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
print((sum_profit/rounds)/(sum_max_value/rounds))
