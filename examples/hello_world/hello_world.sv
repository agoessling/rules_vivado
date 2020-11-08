`default_nettype none

module hello_world #(
    parameter FCLK = 100_000_000,
    parameter BAUD = 9600,
    parameter FREP = 2
) (
    input wire logic i_clk,
    output wire logic o_tx
);

  logic [7:0] msg [0:15];
  initial begin
    msg[0] = "H";
    msg[1] = "e";
    msg[2] = "l";
    msg[3] = "l";
    msg[4] = "o";
    msg[5] = " ";
    msg[6] = "W";
    msg[7] = "o";
    msg[8] = "r";
    msg[9] = "l";
    msg[10] = "d";
    msg[11] = "!";
    msg[12] = "\n";
    msg[13] = "\r";
    msg[14] = 0;
    msg[15] = 0;
  end

  logic tx_strobe;
  logic tx_start;
  logic tx_busy;
  logic [7:0] tx_data;
  logic [3:0] tx_msg_ptr;

  localparam LAST_CHAR = 14;
  initial tx_msg_ptr = LAST_CHAR;

  always_ff @(posedge i_clk) begin
    if (tx_strobe) begin
      tx_msg_ptr <= 0;
    end else if (tx_msg_ptr < LAST_CHAR && !tx_busy) begin
      tx_msg_ptr <= tx_msg_ptr + 1;
    end
  end

  always_comb begin
    tx_data = msg[tx_msg_ptr];

    tx_start = 0;
    if (tx_msg_ptr < LAST_CHAR) begin
      tx_start = 1;
    end
  end

  uart_tx #(.BAUD_DIV($rtoi(FCLK / BAUD))) uart_tx (
      .i_clk,
      .i_reset(1'b0),
      .i_data(tx_data),
      .i_start(tx_start),
      .o_busy(tx_busy),
      .o_tx
  );

  strobe_div #(.DIV($rtoi(FCLK / FREP))) strobe_div (
      .i_clk,
      .i_reset(1'b0),
      .o_strobe(tx_strobe)
  );

endmodule
