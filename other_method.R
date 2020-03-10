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

limited_data <- data[data$Date >= "2017-11-17 00:00:00" & data$Date < "2020-02-09",]

pred = sqrt(sum((limited_data$real_wti - limited_data$p_hat_shifted)^2)/nrow(limited_data))
no = sqrt(sum((limited_data$real_wti - limited_data$no_change)^2)/nrow(limited_data))

pred/no

plot(data$Date, data$real_wti, type="l", col="blue")
lines(data$Date, data$p_hat_shifted, col="red", type="l")

plot(limited_data$Date, limited_data$real_wti, type="l", col="blue")
lines(limited_data$Date, limited_data$p_hat_shifted, col="red", type="l")
lines(limited_data$Date, limited_data$no_change, col="red", type="l")

plot(data$Date, data$p_hat_shifted - data$real_wti, type = "l")
