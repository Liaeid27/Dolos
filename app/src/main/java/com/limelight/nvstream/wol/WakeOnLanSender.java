package com.limelight.nvstream.wol;

import java.io.IOException;
import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.InetAddress;
import java.util.LinkedHashSet;
import com.limelight.nvstream.http.ComputerDetails;

public class WakeOnLanSender {
    // These ports will always be tried as-is.
    private static final int[] STATIC_PORTS_TO_TRY = new int[] {
        9, // Standard WOL port (privileged port)
        47009, // Port opened by Moonlight Internet Hosting Tool for WoL (non-privileged port)
    };

    // These ports will be offset by the base port number (47989) to support alternate ports.
    private static final int[] DYNAMIC_PORTS_TO_TRY = new int[] {
        47998, 47999, 48000, 48002, 48010, // Ports opened by GFE
    };

    private static void sendPacketsForAddress(InetAddress address, int httpPort, DatagramSocket sock, byte[] payload) throws IOException {
        IOException lastException = null;
        boolean sentWolPacket = false;

        // Try the static ports
        for (int port : STATIC_PORTS_TO_TRY) {
            try {
                DatagramPacket dp = new DatagramPacket(payload, payload.length);
                dp.setAddress(address);
                dp.setPort(port);
                sock.send(dp);
                sentWolPacket = true;
            } catch (IOException e) {
                e.printStackTrace();
                lastException = e;
            }
        }

        // Try the dynamic ports
        for (int port : DYNAMIC_PORTS_TO_TRY) {
            int destinationPort = httpPort + (port - 47989);
            if (destinationPort > 65535) {
                continue;
            }
            try {
                DatagramPacket dp = new DatagramPacket(payload, payload.length);
                dp.setAddress(address);
                dp.setPort(destinationPort);
                sock.send(dp);
                sentWolPacket = true;
            } catch (IOException e) {
                e.printStackTrace();
                lastException = e;
            }
        }

        if (!sentWolPacket) {
            throw lastException;
        }
    }
    
    public static void sendWolPacket(ComputerDetails computer) throws IOException {
        try (DatagramSocket socket = new DatagramSocket(0)) {
            sendWolPacket(computer, socket);
        }
    }

    static void sendWolPacket(ComputerDetails computer, DatagramSocket sock) throws IOException {
        byte[] payload = createWolPayload(computer);
        IOException lastException = null;
        boolean sentWolPacket = false;
        LinkedHashSet<ComputerDetails.AddressTuple> targets = new LinkedHashSet<>();
        for (ComputerDetails.AddressTuple target : new ComputerDetails.AddressTuple[] {
                computer.localAddress, computer.manualAddress, computer.remoteAddress,
                computer.ipv6Address, computer.activeAddress}) {
            if (target != null && target.address != null && !target.address.trim().isEmpty() &&
                    target.port > 0 && target.port <= 65535) {
                targets.add(target);
            }
        }
        if (targets.isEmpty()) {
            throw new IOException("Keine PC-Adresse zum Wecken gespeichert.");
        }
        sock.setBroadcast(true);
        // Direct the magic packet to the matching LAN as well as the limited broadcast.
        ComputerDetails.AddressTuple lan=targets.contains(computer.localAddress)?computer.localAddress:targets.iterator().next();
        try{
            byte[] host=InetAddress.getByName(lan.address).getAddress();
            java.util.Enumeration<java.net.NetworkInterface> interfaces=java.net.NetworkInterface.getNetworkInterfaces();
            while(interfaces!=null && interfaces.hasMoreElements()){
                java.net.NetworkInterface nic=interfaces.nextElement();
                if(!nic.isUp()||nic.isLoopback()||nic.isPointToPoint())continue;
                for(java.net.InterfaceAddress addr:nic.getInterfaceAddresses()){
                    InetAddress broadcast=addr.getBroadcast();byte[] ip=addr.getAddress().getAddress();
                    int prefix=addr.getNetworkPrefixLength();
                    if(broadcast==null||host.length!=4||ip.length!=4||prefix<1||prefix>30)continue;
                    boolean matches=true;for(int bit=0;bit<prefix;bit++)
                        if(((host[bit/8]^ip[bit/8])&(128>>(bit%8)))!=0){matches=false;break;}
                    if(matches){sendPacketsForAddress(broadcast,lan.port,sock,payload);sentWolPacket=true;}
                }
            }
        }catch(IOException ignored){}
        // Try all resolved remote and local addresses and broadcast addresses.
        // The broadcast address is required to avoid stale ARP cache entries
        // making the sleeping machine unreachable.
        for (ComputerDetails.AddressTuple address : targets) {
            try {
                sendPacketsForAddress(InetAddress.getByName("255.255.255.255"), address.port, sock, payload);
                sentWolPacket = true;
            } catch (IOException e) {
                e.printStackTrace();
                lastException = e;
            }

            try {
                for (InetAddress resolvedAddress : InetAddress.getAllByName(address.address)) {
                    try {
                        sendPacketsForAddress(resolvedAddress, address.port, sock, payload);
                        sentWolPacket = true;
                    } catch (IOException e) {
                        e.printStackTrace();
                        lastException = e;
                    }
                }
            } catch (IOException e) {
                // We may have addresses that don't resolve on this subnet,
                // but don't throw and exit the whole function if that happens.
                // We'll throw it at the end if we didn't send a single packet.
                e.printStackTrace();
                lastException = e;
            }
        }

        // Propagate the DNS resolution exception if we didn't
        // manage to get a single packet out to the host.
        if (!sentWolPacket && lastException != null) {
            throw lastException;
        }
    }
    
    private static byte[] macStringToBytes(String raw) throws IOException {
        String mac = raw == null ? "" : raw.trim();
        String[] octets;
        if (mac.matches("(?i)[0-9a-f]{12}")) {
            octets = new String[6];
            for (int i = 0; i < octets.length; i++) {
                octets[i] = mac.substring(2 * i, 2 * i + 2);
            }
        } else {
            octets = mac.split(mac.indexOf(':') >= 0 ? ":" : "-", -1);
        }
        if (octets.length != 6) {
            throw new IOException("Die gespeicherte MAC-Adresse ist ungültig.");
        }
        byte[] bytes = new byte[6];
        boolean nonzero = false;
        for (int i = 0; i < bytes.length; i++) {
            if (!octets[i].matches("(?i)[0-9a-f]{1,2}")) {
                throw new IOException("Die gespeicherte MAC-Adresse ist ungültig.");
            }
            bytes[i] = (byte) Integer.parseInt(octets[i], 16);
            nonzero |= bytes[i] != 0;
        }
        if (!nonzero || (bytes[0] & 1) != 0) {
            throw new IOException("Die MAC-Adresse gehört zu keiner einzelnen Netzwerkkarte.");
        }
        return bytes;
    }
    
    private static byte[] createWolPayload(ComputerDetails computer) throws IOException {
        byte[] payload = new byte[102];
        byte[] macAddress = macStringToBytes(computer.macAddress);
        int i;
        
        // 6 bytes of FF
        for (i = 0; i < 6; i++) {
            payload[i] = (byte)0xFF;
        }
        
        // 16 repetitions of the MAC address
        for (int j = 0; j < 16; j++) {
            System.arraycopy(macAddress, 0, payload, i, macAddress.length);
            i += macAddress.length;
        }
        
        return payload;
    }
}
