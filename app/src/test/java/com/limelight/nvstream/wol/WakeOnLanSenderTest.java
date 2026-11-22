package com.limelight.nvstream.wol;

import com.limelight.nvstream.http.ComputerDetails;
import org.junit.Test;

import java.io.IOException;
import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.InetAddress;
import java.net.InetSocketAddress;
import java.net.SocketException;
import java.util.Arrays;

import static org.junit.Assert.*;

public class WakeOnLanSenderTest {
    // Allow only real UDP to our ephemeral listener. No packet leaves the machine.
    private static final class LoopbackSender extends DatagramSocket {
        final int port;
        int attempted;

        LoopbackSender(InetAddress loopback, int port) throws SocketException {
            super(new InetSocketAddress(loopback, 0));
            this.port = port;
        }

        @Override public void send(DatagramPacket packet) throws IOException {
            attempted++;
            if (packet.getAddress().isLoopbackAddress() && packet.getPort() == port) {
                super.send(packet);
            }
        }
    }

    @Test public void sendsCompleteMagicPacketToConfiguredLocalPort() throws Exception {
        InetAddress local = InetAddress.getByName("127.0.0.1");
        try (DatagramSocket listener = new DatagramSocket(0, local);
             LoopbackSender sender = new LoopbackSender(local, listener.getLocalPort())) {
            listener.setSoTimeout(1500);
            ComputerDetails pc = new ComputerDetails();
            // First dynamic port is HTTP port + 9, even for a custom Apollo base port.
            pc.activeAddress = new ComputerDetails.AddressTuple(local.getHostAddress(), listener.getLocalPort()-9);
            byte[] mac = {2, 17, 34, (byte)0x9a, (byte)0xb4, (byte)0xff};
            for (String representation : new String[]{"02:11:22:9a:B4:ff", "02-11-22-9A-B4-FF", "0211229ab4ff"}) {
                pc.macAddress = representation;
                WakeOnLanSender.sendWolPacket(pc, sender);
                DatagramPacket packet = new DatagramPacket(new byte[150], 150);
                listener.receive(packet);
                assertTrue(packet.getAddress().isLoopbackAddress());
                assertEquals(102, packet.getLength());
                for (int i=0; i<6; i++) assertEquals((byte)0xff, packet.getData()[i]);
                for (int i=6; i<102; i+=6) assertArrayEquals(mac, Arrays.copyOfRange(packet.getData(), i, i+6));
            }
        }
    }

    @Test public void rejectsBadMacAndMissingDestinationBeforeSending() throws Exception {
        InetAddress local = InetAddress.getByName("127.0.0.1");
        try (LoopbackSender sender = new LoopbackSender(local, 0)) {
            ComputerDetails pc = new ComputerDetails();
            pc.localAddress = new ComputerDetails.AddressTuple("127.0.0.1", 47989);
            for (String bad : new String[]{null, "", "02:11", "02:11:22:33:44:gg", "00:00:00:00:00:00", "FF:FF:FF:FF:FF:FF", "02:11:22:33:44:55:66"}) {
                pc.macAddress = bad;
                assertThrows(IOException.class, () -> WakeOnLanSender.sendWolPacket(pc, sender));
            }
            pc.macAddress = "02:11:22:33:44:55";
            pc.localAddress = null;
            assertThrows(IOException.class, () -> WakeOnLanSender.sendWolPacket(pc, sender));
            pc.manualAddress = new ComputerDetails.AddressTuple("   ", 47989);
            assertThrows(IOException.class, () -> WakeOnLanSender.sendWolPacket(pc, sender));
            assertEquals(0, sender.attempted);
        }
    }
}
