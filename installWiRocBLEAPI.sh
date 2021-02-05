#!/bin/bash

echo "start update wiroc ble"
WiRocBLEVersion=${1/v/}
sleep 2
systemctl stop WiRocBLEAPI
echo "after stop WiRocBLEAPI"
wget -O WiRoc-BLE-API.tar.gz https://github.com/henla464/WiRoc-BLE-API/archive/v$WiRocBLEVersion.tar.gz
sleep 5
rm -rf WiRoc-BLE-API
echo "after rm"
tar xvfz WiRoc-BLE-API.tar.gz WiRoc-BLE-API-$WiRocBLEVersion
echo "after tar"
mv WiRoc-BLE-API-$WiRocBLEVersion WiRoc-BLE-API

echo "Update WiRocBLE version"
cat << EOF > WiRocBLEVersion.txt
${WiRocBLEVersion}
EOF

echo "after update version"
systemctl start WiRocBLEAPI
echo "after start WiRocBLEAPI"

