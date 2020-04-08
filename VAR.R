library(vars)
formatted_training_data = formatted_training_data[order(formatted_training_data$Date),]
var_training_data<- formatted_training_data[c("watson", "vader", "vader_average", "henry", "WTI")]

var_1 <- VAR(var_training_data, lag.max=10, type="none", ic = "AIC")

fitted <- fitted(var_1)

plot(fitted(var_1)[,"WTI"], type="l", col="blue")
lines(formatted_training_data[4:nrow(formatted_training_data),"WTI"], col="red")

sqrt(mean((fitted(var_1)[,"WTI"]-formatted_training_data[4:nrow(formatted_training_data),"WTI"])^2))

summary(var_1)

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
