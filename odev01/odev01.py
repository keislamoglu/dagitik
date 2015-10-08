import numpy as np
from matplotlib import pyplot as plt

# Mu ve Sigma değerleri atamaları
mu_1, sigma_1 = -3.3, 0.8
mu_2, sigma_2 = 4.7, 1.2

# Ortalama ve standart sapma değerleri kullanılarak rastgele oluşturulan 10000 adetlik diziler
s_1 = np.random.normal(mu_1, sigma_1, 10000)
s_2 = np.random.normal(mu_2, sigma_2, 10000)

# Histogram index haritalamaları için
indexes_1, indexes_2 = range(-20, 21), range(-20, 21)

# İlk değerleri 0 olan histogram dizileri
histogram_1, histogram_2 = [0] * 41, [0] * 41
total_1, total_2 = 0, 0

# Birinci histogram değerleri set ediliyor
for val in s_1:
    int_val = int(val)
    if int_val >= -20 & int_val <= 20:
        histogram_1[indexes_1.index(int_val)] += 1
        total_1 += 1
# Birinci histogram için normalizasyon işlemi
for index, val in enumerate(histogram_1):
    histogram_1[index] = val / total_1

# İkinci histogram değerleri set ediliyor
for val in s_2:
    int_val = int(val)
    if int_val >= -20 & int_val <= 20:
        histogram_2[indexes_2.index(int_val)] += 1
        total_2 += 1

# İkinci histogram için normalizasyon işlemi
for index, val in enumerate(histogram_2):
    histogram_2[index] = val / total_2

# Birinci histogram barı oluşturuluyor
plt.bar(indexes_1, histogram_1, width=1, color='r', alpha=0.5)

# İkinci histogram barı oluşturuluyor
plt.bar(indexes_2, histogram_2, width=1, color='b', alpha=0.5)

# Histogramın x ekseni limitleri belirleniyor
plt.xlim(-20, 20)

# distance hesaplanıyor
i, j, distance = 0, 0, 0
while (j < len(histogram_2) - 1) & (i < len(histogram_1) - 1):
    if histogram_2[j] > 0:
        while (i < len(histogram_1) - 1) & (histogram_1[i] == 0):
            i += 1
        distance += abs(i-j) * histogram_1[i]
        if histogram_2[j] > histogram_1[i]:
            histogram_2[j] -= histogram_1[i]
            histogram_1[i] = 0
        else:
            histogram_1[i] -= histogram_2[j]
            histogram_2[j] = 0
    else:
        j += 1
# distance ekrana bastırılıyor
print('Distance: ' + str(distance))

# Histogram çizdiriliyor
plt.show()
