library(vars)
formatted_training_data = formatted_training_data[order(formatted_training_data$Date),]
var_training_data<- formatted_training_data[c("watson", "vader", "vader_average", "Loughran.McDonald", "henry", "WTI")]

var_1 <- VAR(var_training_data, lag.max=10, type="none", ic = "AIC")

fitted <- fitted(var_1)

plot(fitted(var_1)[,"WTI"], type="l", col="red")
lines(formatted_training_data[4:nrow(formatted_training_data),"WTI"], col="blue")

sqrt(mean((fitted(var_1)[,"WTI"]-formatted_training_data[4:nrow(formatted_training_data),"WTI"])^2))

summary(var_1)

ar <- arima(formatted_training_data$WTI, order=c(3, 0, 0))
y_hat <- formatted_training_data$WTI-ar$residuals
sqrt(mean((ar$residuals)^2))
plot(formatted_training_data$WTI, type="l", col="blue")
lines(formatted_training_data$WTI-ar$residuals, col="red")

ir.1 <- irf(var_1, impulse = "watson", response = "WTI", n.ahead = 20, ortho = FALSE)
plot(ir.1)

(fitted(var_1)[,"WTI"]-formatted_training_data[4:nrow(formatted_training_data),"WTI"])^2

limited_data$Date <- format(as.POSIXct(limited_data$Date,format='%Y-%m-%d %H:%M:%S'),format='%Y-%m-%d')

plot_data = formatted_training_data[c("Date", "WTI")]
plot_data$no_change = NA
plot_data$no_change[2:nrow(plot_data)] = plot_data$WTI[1:nrow(plot_data)-1]
plot_data$VAR = NA
plot_data$VAR[4:nrow(plot_data)] = fitted(var_1)[,"WTI"]
plot_data$spread = NA
plot_data$inflation = NA
for(i in rownames(plot_data)){
  price = limited_data[limited_data$Date == plot_data[i, "Date"], "p_hat_shifted"]
  inflation = limited_data[limited_data$Date == plot_data[i, "Date"], "inflation_2015"]
  if(length(price)>0){
    plot_data[i, "spread"] = price
    plot_data[i, "inflation"] = inflation
  }
}
plot_data$spread = plot_data$spread*(plot_data$inflation/100)

plot_data$machine = NA
plot_data$machine[4:nrow(plot_data)] = out_test$X1

plot_data$Date = as.POSIXct(plot_data$Date,format='%Y-%m-%d')

plot(x=, y=plot_data$WTI, type="l", col="blue")

plot(WTI ~ Date, plot_data, col="blue", type="l")
lines(no_change ~ Date, plot_data, col="red", type="l", lty=2)
lines(VAR ~ Date, plot_data, col="darkgreen", type="l", lty=3)
lines(machine ~ Date, plot_data, col="goldenrod3", type="l", lty=2)
legend(x="bottomleft", legend=c("WTI", "No Change", "VAR", "Machine Learning"), col=c("blue", "red", "darkgreen", "goldenrod3"), lty=c(1,2,3,2))


prediction = fitted[,"WTI"]

sum_profit = 0
sum_max_value = 0
rounds = 1

for(i in 1:rounds){
  max_value = 0
  barrels = 0
  value = 0
  profit = 0
  
  for(index in 3:(length(formatted_training_data$WTI)-1)){
    current_price = formatted_training_data$WTI[index]
    if(prediction[(index-2)] > current_price ){
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