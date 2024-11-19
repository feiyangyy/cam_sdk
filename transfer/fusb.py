import usb.core
import usb.util


import struct

"""
            TRANSFER_TYPE_CONTROL
            TRANSFER_TYPE_ISOCHRONOUS
            TRANSFER_TYPE_BULK
            TRANSFER_TYPE_INTERRUPT
"""

class PacketSovler(object):
  MAGIC=b'NEXT_VPU'
  PKT_LEN=2+2+4+4
  def __init__(self, buffer_size):
    self.buffer_ = bytearray(buffer_size)
    # the next empty point.
    self.cur_idx = 0
    self.MAX_LEN = buffer_size
    
  def OnDataRead(self, data:bytearray):
    """
    Return one or more packet, or none.
    """
    if len(data) + self.cur_idx >= self.MAX_LEN:
      print("Unable to solve data!")
      diff = self.MAX_LEN- self.cur_idx
      self.buffer_[self.cur_idx: self.MAX_LEN] = data[0: diff]
      self.cur_idx = self.MAX_LEN
    else:
      self.buffer_[self.cur_idx: self.cur_idx + len(data)] = data[:len(data)]
      self.cur_idx += len(data)
    pkts = self.SolvePacket()
    if(len(pkts)):
      print(f"Get {len(pkts)} packets!")

  def SolvePacket(self):
    pkt_idx = 0
    max_len = self.cur_idx
    packets = []
    while True:
      # 不足以解出一个包
      if max_len - pkt_idx < 8 + self.PKT_LEN:
        break
      if self.buffer_[pkt_idx:8] == self.MAGIC:
        headers = struct.unpack("<HHII", self.buffer_[pkt_idx + 8: pkt_idx + 8 + self.PKT_LEN])
        data_len = headers[3]
        # 判断数据区域是否足够
        pkt_len = 8 + self.PKT_LEN + data_len
        if pkt_idx + pkt_len > max_len:
          # 不满足解出一个包的条件
          break
        packets.append(self.buffer_[pkt_idx: pkt_idx + pkt_len])
        pkt_idx += pkt_len
        continue
      # 寻找包头
      pkt_idx += 1
      continue
    tail = max_len - pkt_idx
    if tail > 0:
      self.buffer_[0: tail] = self.buffer_[pkt_idx: max_len]
      self.cur_idx = tail
    else:
      self.cur_idx = 0
    return packets


class FeymanUSB(object):
  MAX_PACKET_SIZE = 4 * 1024 * 1024 + 1024
  
  FM_IDS = [
    [0x4E56, 0x5055],
    [0x4E56, 0x5056],
    [0x2BDF, 0x0001],
    [0x4E56, 0x594E],
  ]
  def __init__(self):
    # self.ctx = usb1.USBContext()
    self.dev = None
    self.hnd = None
  
  def FindFeyman(self):
    dev = None
    for fm in self.FM_IDS:
      dev = usb.core.find(idVendor=fm[0], idProduct=fm[1])
      if dev is None:
        continue
      print(f"Found {fm[0]:04x}:{fm[1]:04x}")
      print(dev)
      break
    print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
    if dev.is_kernel_driver_active(0):
      print("Detach kernel drvier!")
      dev.detach_kernel_driver(0)
    usb.util.claim_interface(dev, 0)
    cfg = dev.get_active_configuration()
    interface_in = cfg[(0, 0)]
    # 找到第一个满足条件的，或者，使用findall 获取全部
    epi  = usb.util.find_descriptor(interface_in.endpoints(), custom_match=lambda e:usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_IN)
    print(epi)
    epo = usb.util.find_descriptor(interface_in.endpoints(), find_all=False, custom_match=lambda e:usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT)
    print(epo)
    print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
    solver = PacketSovler(self.MAX_PACKET_SIZE)
    while True:
      try:
        dr = dev.read(epi.bEndpointAddress, self.MAX_PACKET_SIZE)
        # print(dr)
        solver.OnDataRead(dr)
      except usb.core.USBError as e:
        print("fucked by ", e)
    
  

if __name__ == "__main__":
  fusb = FeymanUSB()
  fusb.FindFeyman()